import cv2
import time
import threading
from flask import Flask, Response

app = Flask(__name__)

CAMERA_URL = "rtsp://admin:xx2317xx2317@182.76.136.44:8554/streaming/channels/201"

current_frame = None
lock = threading.Lock()

def camera_reader_thread():
    global current_frame
    while True:
        print(f"[Relay] Connecting to camera: {CAMERA_URL}")
        cap = cv2.VideoCapture(CAMERA_URL)
        if not cap.isOpened():
            print("[Relay] Retrying camera connection in 3s...")
            time.sleep(3)
            continue

        print("[Relay] ✅ Connected to camera stream!")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Relay] Stream disconnected. Reconnecting...")
                break
            
            with lock:
                current_frame = frame.copy()
            
            time.sleep(0.01)
        
        cap.release()
        time.sleep(2)

def generate_mjpeg():
    global current_frame
    while True:
        frame = None
        with lock:
            if current_frame is not None:
                frame = current_frame.copy()

        if frame is None:
            time.sleep(0.05)
            continue

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        time.sleep(0.04)

@app.route('/stream')
def stream():
    return Response(generate_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("==============================================")
    print("  PYTHON CAMERA STREAM RELAY SERVER (Port 5001)")
    print("==============================================")
    
    t = threading.Thread(target=camera_reader_thread, daemon=True)
    t.start()
    
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False, threaded=True)
