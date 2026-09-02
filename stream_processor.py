import threading
import time
import uuid
import cv2
import numpy as np
import config
from detector import PersonDetector

class StreamProcessor:
    def __init__(self):
        self.detector = PersonDetector()
        
        # Camera management
        self.cameras = config.load_cameras()
        self.active_camera = self.cameras[0] if self.cameras else {
            "id": "default", "name": "Default", "url": config.DEFAULT_RTSP_URL, "location": "Default"
        }
        self.rtsp_url = self.active_camera["url"]
        
        self.running = False
        self.connected = False
        self.paused = False
        
        # Thread handles
        self.reader_thread = None
        self.processor_thread = None
        self.lock = threading.Lock()
        
        # Frame buffers
        self.raw_frame = None
        self.processed_frame = None
        self.detections = []
        
        # Statistics
        self.fps = 0.0
        self.current_count = 0
        self.peak_count = 0
        self.total_frames = 0
        
        # Detection history logs
        self.detection_logs = []

    def start(self):
        """Start the background streaming and processing threads."""
        if not self.running:
            self.running = True
            self.reader_thread = threading.Thread(target=self._reader_loop, name="RTSPReader", daemon=True)
            self.processor_thread = threading.Thread(target=self._processor_loop, name="FrameProcessor", daemon=True)
            self.reader_thread.start()
            self.processor_thread.start()
            print(f"StreamProcessor started for camera: {self.active_camera['name']}")

    def stop(self):
        """Stop all background threads and release resources."""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=2.0)
        if self.processor_thread:
            self.processor_thread.join(timeout=2.0)
        print("StreamProcessor threads stopped.")

    # Camera Management CRUD APIs
    def get_cameras(self):
        """Get full list of configured cameras and active ID."""
        with self.lock:
            return {
                "cameras": self.cameras,
                "active_id": self.active_camera["id"]
            }

    def switch_camera(self, cam_id):
        """Switch active RTSP stream to a different camera."""
        with self.lock:
            target = next((c for c in self.cameras if c["id"] == cam_id), None)
            if not target:
                return False, "Camera ID not found"
            
            self.active_camera = target
            self.rtsp_url = target["url"]
            self.connected = False
            self.raw_frame = None
            self.processed_frame = None
            self.current_count = 0
            self.peak_count = 0
            print(f"Switched active camera to: {target['name']} ({target['url']})")
            return True, "Switched successfully"

    def add_camera(self, name, url, location=""):
        """Add a new camera and optionally save to disk."""
        with self.lock:
            cam_id = f"cam_{uuid.uuid4().hex[:6]}"
            new_cam = {
                "id": cam_id,
                "name": name.strip(),
                "url": url.strip(),
                "location": location.strip()
            }
            self.cameras.append(new_cam)
            config.save_cameras(self.cameras)
            return new_cam

    def edit_camera(self, cam_id, name, url, location=""):
        """Edit details of an existing camera."""
        with self.lock:
            cam = next((c for c in self.cameras if c["id"] == cam_id), None)
            if not cam:
                return False, "Camera not found"
            
            cam["name"] = name.strip()
            cam["url"] = url.strip()
            cam["location"] = location.strip()
            
            # If editing active camera, update stream URL immediately
            if self.active_camera["id"] == cam_id:
                self.active_camera = cam
                self.rtsp_url = cam["url"]
                self.connected = False
                
            config.save_cameras(self.cameras)
            return True, "Updated successfully"

    def delete_camera(self, cam_id):
        """Delete a camera from configuration."""
        with self.lock:
            if len(self.cameras) <= 1:
                return False, "Cannot delete the only remaining camera"
                
            self.cameras = [c for c in self.cameras if c["id"] != cam_id]
            
            # If deleted camera was active, switch to first available camera
            if self.active_camera["id"] == cam_id:
                self.active_camera = self.cameras[0]
                self.rtsp_url = self.active_camera["url"]
                self.connected = False
                
            config.save_cameras(self.cameras)
            return True, "Deleted successfully"

    def update_settings(self, conf_threshold, nms_threshold):
        """Update detection engine thresholds on the fly."""
        with self.lock:
            self.detector.set_thresholds(conf_threshold, nms_threshold)

    def toggle_pause(self):
        """Toggle stream processing between paused and active."""
        with self.lock:
            self.paused = not self.paused
            return self.paused

    def get_stats(self):
        """Get copy of current status, telemetry, and camera metadata."""
        with self.lock:
            return {
                "connected": self.connected,
                "paused": self.paused,
                "fps": round(self.fps, 1),
                "current_count": self.current_count,
                "peak_count": self.peak_count,
                "total_frames": self.total_frames,
                "active_camera": self.active_camera,
                "logs": list(self.detection_logs)
            }

    def get_frame_jpeg(self):
        """Encodes the processed frame as JPEG. Returns offline HUD if disconnected."""
        with self.lock:
            # 1. Offline Frame Generator
            if not self.connected:
                offline_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # Tech-grid background
                for i in range(0, 640, 40):
                    cv2.line(offline_frame, (i, 0), (i, 480), (25, 25, 25), 1)
                for j in range(0, 480, 40):
                    cv2.line(offline_frame, (0, j), (640, j), (25, 25, 25), 1)
                
                # Text labels
                cv2.putText(offline_frame, f"CAMERA OFFLINE: {self.active_camera['name'].upper()}", (90, 210), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                
                url_display = self.rtsp_url
                if len(url_display) > 40:
                    url_display = "rtsp://***@" + self.rtsp_url.split("@")[-1] if "@" in self.rtsp_url else self.rtsp_url[:40]
                
                cv2.putText(offline_frame, f"Target: {url_display}", (80, 250), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 130, 130), 1, cv2.LINE_AA)
                cv2.putText(offline_frame, "Retrying TCP RTSP Connection...", (180, 280), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 240, 255), 1, cv2.LINE_AA)
                
                # Pulsing indicator
                dot_color = (0, 0, 255) if int(time.time()) % 2 == 0 else (40, 40, 40)
                cv2.circle(offline_frame, (65, 204), 7, dot_color, -1)
                
                ret, jpeg = cv2.imencode('.jpg', offline_frame)
                return jpeg.tobytes() if ret else None

            # 2. Initializing frame
            if self.processed_frame is None:
                loading_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(loading_frame, f"CONNECTING TO {self.active_camera['name'].upper()}...", (120, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1, cv2.LINE_AA)
                ret, jpeg = cv2.imencode('.jpg', loading_frame)
                return jpeg.tobytes() if ret else None

            # 3. Processed Frame
            ret, jpeg = cv2.imencode('.jpg', self.processed_frame)
            return jpeg.tobytes() if ret else None

    def _reader_loop(self):
        """Continuously pulls frames using TCP transport FFmpeg options."""
        while self.running:
            target_url = self.rtsp_url
            cam_name = self.active_camera["name"]
            print(f"Connecting RTSP via TCP to [{cam_name}]: {target_url}")
            
            cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                print(f"Failed to connect to {cam_name}. Retrying in 5s...")
                with self.lock:
                    self.connected = False
                time.sleep(5)
                continue

            with self.lock:
                self.connected = True
            print(f"Successfully connected to RTSP stream: {cam_name}")

            while self.running and self.rtsp_url == target_url:
                ret, frame = cap.read()
                if not ret:
                    print(f"RTSP stream disconnected for {cam_name}. Retrying...")
                    with self.lock:
                        self.connected = False
                        self.raw_frame = None
                    break

                with self.lock:
                    self.raw_frame = frame
                
                time.sleep(0.002)

            cap.release()
            time.sleep(0.5)

    def _processor_loop(self):
        """Runs detection pipeline and records counts and log events."""
        last_fps_time = time.time()
        frame_count = 0

        while self.running:
            if self.paused:
                with self.lock:
                    if self.raw_frame is not None:
                        h, w = self.raw_frame.shape[:2]
                        paused_frame = self.raw_frame.copy()
                        overlay = paused_frame.copy()
                        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
                        cv2.addWeighted(overlay, 0.5, paused_frame, 0.5, 0, paused_frame)
                        
                        cv2.rectangle(paused_frame, (w//2 - 140, h//2 - 25), (w//2 + 140, h//2 + 25), (255, 0, 180), 1)
                        cv2.putText(paused_frame, "MONITORING PAUSED", (w//2 - 110, h//2 + 6), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 180), 1, cv2.LINE_AA)
                        
                        self.processed_frame = paused_frame
                        self.current_count = 0
                time.sleep(0.1)
                continue

            frame = None
            with self.lock:
                if self.raw_frame is not None:
                    frame = self.raw_frame.copy()

            if frame is None:
                time.sleep(0.01)
                continue

            proc_frame, detections = self.detector.detect(frame)
            count = len(detections)

            # Draw camera name banner on frame top-right
            h_f, w_f = proc_frame.shape[:2]
            cam_label = f"CAM: {self.active_camera['name'].upper()}"
            cv2.putText(proc_frame, cam_label, (w_f - 240, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 255), 1, cv2.LINE_AA)

            with self.lock:
                self.processed_frame = proc_frame
                self.detections = detections
                
                if count != self.current_count:
                    timestamp = time.strftime("%H:%M:%S")
                    event_type = "Detection" if count > self.current_count else "Clearance"
                    self.detection_logs.append({
                        "timestamp": timestamp,
                        "count": count,
                        "event": event_type,
                        "camera": self.active_camera["name"],
                        "details": f"Count changed to {count}"
                    })
                    if len(self.detection_logs) > 40:
                        self.detection_logs.pop(0)

                self.current_count = count
                if count > self.peak_count:
                    self.peak_count = count

            frame_count += 1
            self.total_frames += 1

            now = time.time()
            elapsed = now - last_fps_time
            if elapsed >= 1.0:
                self.fps = frame_count / elapsed
                frame_count = 0
                last_fps_time = now

            time.sleep(0.01)
