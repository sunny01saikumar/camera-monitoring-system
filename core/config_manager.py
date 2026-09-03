import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
KNOWN_FACES_DIR = os.path.join(DATA_DIR, "known_faces")
ALERTS_DIR = os.path.join(DATA_DIR, "alerts")
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.onnx")
CAMERAS_FILE = os.path.join(BASE_DIR, "cameras.json")
SMTP_FILE = os.path.join(DATA_DIR, "smtp_config.json")
SERVICES_FILE = os.path.join(DATA_DIR, "services_config.json")

# Ensure required directories exist
for path in [DATA_DIR, KNOWN_FACES_DIR, ALERTS_DIR, MODEL_DIR]:
    os.makedirs(path, exist_ok=True)

# Default fallback RTSP URL
DEFAULT_RTSP_URL = "rtsp://admin:xx2317xx2317@182.76.136.44:8554/streaming/channels/201"

def load_smtp_config():
    """Load Gmail SMTP configuration."""
    if os.path.exists(SMTP_FILE):
        try:
            with open(SMTP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {SMTP_FILE}: {e}")
            
    default_config = {
        "enabled": False,
        "sender_email": "",
        "app_password": "",
        "recipient_email": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "cooldown_seconds": 180
    }
    save_smtp_config(default_config)
    return default_config

def save_smtp_config(cfg):
    """Save Gmail SMTP configuration."""
    try:
        with open(SMTP_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving {SMTP_FILE}: {e}")

def load_services_config():
    """Load OSGi service activation toggles."""
    if os.path.exists(SERVICES_FILE):
        try:
            with open(SERVICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {SERVICES_FILE}: {e}")

    default_config = {
        "camera_service": True,
        "yolo_detection_service": True,
        "face_recognition_service": True,
        "gmail_notifier_service": False
    }
    save_services_config(default_config)
    return default_config

def save_services_config(cfg):
    """Save OSGi service activation states."""
    try:
        with open(SERVICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving {SERVICES_FILE}: {e}")
