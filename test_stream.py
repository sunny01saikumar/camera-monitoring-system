import cv2
import socket
import time

url = "rtsp://admin:xx2317xx2317@182.76.136.44:8554/streaming/channels/201"
ip = "182.76.136.44"
port = 8554

print("==============================================")
print("  RTSP CAMERA DIAGNOSTIC TEST")
print("==============================================")

# 1. Test TCP Port Connectivity
print(f"\n1. Testing network port connectivity to {ip}:{port}...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
try:
    s.connect((ip, port))
    print(f"   [SUCCESS] Port {port} is OPEN and reachable from this device!")
    s.close()
except Exception as e:
    print(f"   [FAILED] Cannot reach {ip}:{port} - Network error: {e}")
    print("   -> Explanation: This machine's network or firewall cannot reach port 8554 on 182.76.136.44.")

# 2. Test OpenCV standard RTSP capture
print("\n2. Testing OpenCV default VideoCapture...")
cap = cv2.VideoCapture(url)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"   [SUCCESS] Successfully captured frame! Resolution: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("   [FAILED] Connected to RTSP stream, but frame read returned False.")
    cap.release()
else:
    print("   [FAILED] OpenCV could not open RTSP stream.")

# 3. Test OpenCV with explicit URL query parameters
print("\n3. Testing OpenCV with RTSP transport query parameters...")
urls_to_test = [
    url + "?tcp",
    url + "?transport=udp",
    url.replace("8554", "554") # Test standard RTSP port 554 if 8554 is mapped
]

for test_url in urls_to_test:
    print(f"   Testing: {test_url}")
    cap = cv2.VideoCapture(test_url)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"      [SUCCESS] Captured frame! Shape: {frame.shape}")
            cap.release()
            break
        cap.release()

print("\n==============================================")
