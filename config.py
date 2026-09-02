import os
import json

# Centralized configuration parameters for RTSP Person Detection

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.onnx")
CAMERAS_FILE = os.path.join(BASE_DIR, "cameras.json")

# Pre-trained Weights URL
MODEL_URL = "https://huggingface.co/unity/inference-engine-yolo/resolve/main/models/yolov8n.onnx"

# Default Model Inference Parameters
DEFAULT_CONF_THRESHOLD = 0.40
DEFAULT_NMS_THRESHOLD = 0.40
INPUT_WIDTH = 640
INPUT_HEIGHT = 640

# Server configurations
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Fallback RTSP URL if cameras.json is missing
DEFAULT_RTSP_URL = "rtsp://admin:xx2317xx2317@182.76.136.44:8554/streaming/channels/201"

def load_cameras():
    """Load list of configured cameras from cameras.json."""
    if os.path.exists(CAMERAS_FILE):
        try:
            with open(CAMERAS_FILE, 'r', encoding='utf-8') as f:
                cameras = json.load(f)
                if isinstance(cameras, list) and len(cameras) > 0:
                    return cameras
        except Exception as e:
            print(f"Error reading {CAMERAS_FILE}: {e}")
            
    # Default camera fallback
    default_cameras = [
        {
            "id": "cam_1",
            "name": "Main Camera",
            "url": DEFAULT_RTSP_URL,
            "location": "Primary Stream"
        }
    ]
    save_cameras(default_cameras)
    return default_cameras

def save_cameras(cameras):
    """Save list of cameras to cameras.json."""
    try:
        with open(CAMERAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cameras, f, indent=2)
    except Exception as e:
        print(f"Error saving to {CAMERAS_FILE}: {e}")
