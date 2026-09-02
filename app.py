import time
from flask import Flask, render_template, Response, jsonify, request
import config
from stream_processor import StreamProcessor

app = Flask(__name__)

# Global Stream Processor instance
processor = StreamProcessor()

@app.route('/')
def index():
    """Serves the main application dashboard."""
    return render_template('index.html')

def gen_frames():
    """Generator function that yields MJPEG video stream."""
    while True:
        frame_bytes = processor.get_frame_jpeg()
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
    """Returns JSON payload of system telemetry, stats, and logs."""
    return jsonify(processor.get_stats())

# Camera Management APIs
@app.route('/api/cameras', methods=['GET'])
def api_get_cameras():
    """Get list of all configured cameras and active camera ID."""
    return jsonify(processor.get_cameras())

@app.route('/api/cameras/switch', methods=['POST'])
def api_switch_camera():
    """Switch active streaming camera."""
    data = request.get_json() or {}
    cam_id = data.get("id")
    if not cam_id:
        return jsonify({"status": "error", "message": "Missing camera id"}), 400
    
    success, msg = processor.switch_camera(cam_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route('/api/cameras/add', methods=['POST'])
def api_add_camera():
    """Add a new RTSP camera stream."""
    data = request.get_json() or {}
    name = data.get("name")
    url = data.get("url")
    location = data.get("location", "")
    
    if not name or not url:
        return jsonify({"status": "error", "message": "Camera name and RTSP URL are required"}), 400
        
    new_cam = processor.add_camera(name, url, location)
    return jsonify({"status": "success", "camera": new_cam})

@app.route('/api/cameras/edit', methods=['POST'])
def api_edit_camera():
    """Edit existing camera stream configuration."""
    data = request.get_json() or {}
    cam_id = data.get("id")
    name = data.get("name")
    url = data.get("url")
    location = data.get("location", "")
    
    if not cam_id or not name or not url:
        return jsonify({"status": "error", "message": "ID, name, and RTSP URL are required"}), 400
        
    success, msg = processor.edit_camera(cam_id, name, url, location)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route('/api/cameras/delete', methods=['POST'])
def api_delete_camera():
    """Delete a camera from system."""
    data = request.get_json() or {}
    cam_id = data.get("id")
    if not cam_id:
        return jsonify({"status": "error", "message": "Missing camera id"}), 400
        
    success, msg = processor.delete_camera(cam_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route('/api/settings', methods=['POST'])
def api_settings():
    """Handles runtime thresholds adjustments and stream pausing."""
    data = request.get_json() or {}
    
    if 'conf_threshold' in data and 'nms_threshold' in data:
        try:
            conf = float(data['conf_threshold'])
            nms = float(data['nms_threshold'])
            if 0.0 <= conf <= 1.0 and 0.0 <= nms <= 1.0:
                processor.update_settings(conf, nms)
            else:
                return jsonify({"status": "error", "message": "Thresholds must be between 0.0 and 1.0"}), 400
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid float"}), 400

    if data.get('action') == 'toggle_pause':
        paused_state = processor.toggle_pause()
        return jsonify({"status": "success", "paused": paused_state})
        
    return jsonify({"status": "success", "message": "Settings updated"})

# Ensure background processor starts when loaded
processor.start()

if __name__ == '__main__':
    print(f"Launching web interface on http://{config.HOST}:{config.PORT}")
    try:
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        processor.stop()
