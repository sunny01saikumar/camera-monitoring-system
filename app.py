import os
import time
from flask import Flask, render_template, Response, jsonify, request
from werkzeug.utils import secure_filename

import config
import core.config_manager as config_mgr
from core.framework import framework, ServiceState

# Import OSGi plugin bundles to register services into framework
import plugins.ai_analytics
import plugins.gmail_notifier
from stream_processor import stream_service

app = Flask(__name__)

# Start default core OSGi services on startup
framework.start_service("camera_service")
framework.start_service("ai_analytics_service")

@app.route('/')
def index():
    """Serves the main OSGi application dashboard."""
    return render_template('index.html')

def gen_frames():
    """Generator function yielding MJPEG video stream."""
    while True:
        frame_bytes = stream_service.get_frame_jpeg()
        if frame_bytes is None:
            time.sleep(0.03)
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)

@app.route('/video_feed')
def video_feed():
    """MJPEG stream endpoint."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def api_stats():
    """Returns system telemetry, stats, logs, and active OSGi service states."""
    return jsonify(stream_service.get_stats())

# -------------------------------------------------------------
# OSGi Service Lifecycle APIs (On-Demand Service Toggles)
# -------------------------------------------------------------
@app.route('/api/osgi/services', methods=['GET'])
def api_osgi_services():
    """Returns the state of all OSGi services."""
    return jsonify(framework.get_service_states())

@app.route('/api/osgi/toggle', methods=['POST'])
def api_osgi_toggle():
    """Dynamically activates or deactivates an OSGi service bundle on-demand."""
    data = request.get_json() or {}
    service_id = data.get("service_id")
    enable = data.get("enable", True)

    if not service_id:
        return jsonify({"status": "error", "message": "Missing service_id"}), 400

    if enable:
        success = framework.start_service(service_id)
    else:
        success = framework.stop_service(service_id)

    # Save preference
    services_cfg = config_mgr.load_services_config()
    services_cfg[service_id] = enable
    config_mgr.save_services_config(services_cfg)

    return jsonify({
        "status": "success" if success else "error",
        "service_id": service_id,
        "state": framework.get_service_states().get(service_id)
    })

# -------------------------------------------------------------
# Camera Management APIs
# -------------------------------------------------------------
@app.route('/api/cameras', methods=['GET'])
def api_get_cameras():
    return jsonify(stream_service.get_cameras())

@app.route('/api/cameras/switch', methods=['POST'])
def api_switch_camera():
    data = request.get_json() or {}
    cam_id = data.get("id")
    if not cam_id:
        return jsonify({"status": "error", "message": "Missing camera id"}), 400
    
    success, msg = stream_service.switch_camera(cam_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route('/api/cameras/add', methods=['POST'])
def api_add_camera():
    data = request.get_json() or {}
    name = data.get("name")
    url = data.get("url")
    location = data.get("location", "")
    
    if not name or not url:
        return jsonify({"status": "error", "message": "Camera name and URL required"}), 400
        
    new_cam = stream_service.add_camera(name, url, location)
    return jsonify({"status": "success", "camera": new_cam})

@app.route('/api/cameras/edit', methods=['POST'])
def api_edit_camera():
    data = request.get_json() or {}
    cam_id = data.get("id")
    name = data.get("name")
    url = data.get("url")
    location = data.get("location", "")
    
    if not cam_id or not name or not url:
        return jsonify({"status": "error", "message": "ID, name, and URL required"}), 400
        
    success, msg = stream_service.edit_camera(cam_id, name, url, location)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route('/api/cameras/delete', methods=['POST'])
def api_delete_camera():
    data = request.get_json() or {}
    cam_id = data.get("id")
    if not cam_id:
        return jsonify({"status": "error", "message": "Missing camera id"}), 400
        
    success, msg = stream_service.delete_camera(cam_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

# -------------------------------------------------------------
# Gmail SMTP Settings APIs
# -------------------------------------------------------------
@app.route('/api/smtp', methods=['GET', 'POST'])
def api_smtp():
    if request.method == 'GET':
        return jsonify(config_mgr.load_smtp_config())
    
    data = request.get_json() or {}
    config_mgr.save_smtp_config(data)
    
    # Auto-activate or deactivate Gmail Notifier service in OSGi framework
    if data.get("enabled"):
        framework.start_service("gmail_notifier_service")
    else:
        framework.stop_service("gmail_notifier_service")

    return jsonify({"status": "success", "message": "SMTP configuration saved."})

# -------------------------------------------------------------
# Known Faces Management APIs
# -------------------------------------------------------------
@app.route('/api/faces', methods=['GET'])
def api_get_faces():
    """Lists all uploaded known faces."""
    faces = []
    known_dir = config_mgr.KNOWN_FACES_DIR
    if os.path.exists(known_dir):
        for f in os.listdir(known_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                name = os.path.splitext(f)[0].replace("_", " ").title()
                faces.append({"filename": f, "name": name})
    return jsonify({"faces": faces})

@app.route('/api/faces/upload', methods=['POST'])
def api_upload_face():
    """Upload a new known person photo."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    file = request.files['file']
    person_name = request.form.get('name', '').strip()
    
    if not person_name or file.filename == '':
        return jsonify({"status": "error", "message": "Person name and file required"}), 400

    filename = secure_filename(f"{person_name.replace(' ', '_')}.jpg")
    save_path = os.path.join(config_mgr.KNOWN_FACES_DIR, filename)
    file.save(save_path)

    # Reload known faces in AI Analytics service
    ai_service = framework.get_service("ai_analytics_service")
    if ai_service:
        ai_service.load_known_faces()

    return jsonify({"status": "success", "filename": filename, "name": person_name})

@app.route('/api/settings', methods=['POST'])
def api_settings():
    data = request.get_json() or {}
    
    if 'conf_threshold' in data and 'nms_threshold' in data:
        try:
            conf = float(data['conf_threshold'])
            nms = float(data['nms_threshold'])
            ai_service = framework.get_service("ai_analytics_service")
            if ai_service:
                ai_service.conf_threshold = conf
                ai_service.nms_threshold = nms
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid float"}), 400

    if data.get('action') == 'toggle_pause':
        paused_state = stream_service.toggle_pause()
        return jsonify({"status": "success", "paused": paused_state})
        
    return jsonify({"status": "success", "message": "Settings updated"})

if __name__ == '__main__':
    print(f"Launching OSGi Web Server on http://{config.HOST}:{config.PORT}")
    try:
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        framework.stop_service("camera_service")
        framework.stop_service("ai_analytics_service")
        framework.stop_service("gmail_notifier_service")
