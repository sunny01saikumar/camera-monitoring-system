import cv2
import time
from flask import Flask, Response

app = Flask(__name__)

# Target camera URL accessible from this Windows PC
CAMERA_URL = "rtsp://admin:xx2317xx2317@182.76.136.44:8554/streaming/channels/201"

print(f"Connecting to camera stream: {CAMERA_URL}")
cap = cv2.VideoCapture(CAMERA_URL)

def generate_frames():
    while True:
        if not cap.isOpened():
            time.sleep(1)
            continue
            
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
            
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.03)

@app.route('/stream')
def video_stream():
    """HTTP MJPEG Relay Stream Endpoint."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("==============================================")
    print("  PYTHON CAMERA STREAM RELAY SERVER (Port 5001)")
    print("  Sharing stream to Raspberry Pi & remote devices")
    print("==============================================")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
