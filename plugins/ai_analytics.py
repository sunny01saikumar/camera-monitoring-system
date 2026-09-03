import os
import cv2
import numpy as np
import config
import core.config_manager as config_mgr
from core.framework import framework

class AIAnalyticsService:
    """
    OSGi Service Bundle: AI Analytics Engine.
    Executes YOLOv8 person detection and Known vs Unknown person classification.
    Publishes 'UNKNOWN_PERSON_ALERT' events to the OSGi EventBus when unrecognized faces appear.
    """
    def __init__(self):
        self.net = cv2.dnn.readNet(config.MODEL_PATH)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        
        self.conf_threshold = config.DEFAULT_CONF_THRESHOLD
        self.nms_threshold = config.DEFAULT_NMS_THRESHOLD
        self.target_class_id = 0 # COCO person class
        
        self.known_face_histograms = {} # name -> Color Histogram / Face Template
        self.load_known_faces()

    def start(self):
        print("[OSGi Plugin] AIAnalyticsService ACTIVE.")

    def stop(self):
        print("[OSGi Plugin] AIAnalyticsService RESOLVED.")

    def load_known_faces(self):
        """Loads and computes feature templates for images in data/known_faces/."""
        self.known_face_histograms = {}
        known_dir = config_mgr.KNOWN_FACES_DIR
        
        if not os.path.exists(known_dir):
            return

        for filename in os.listdir(known_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(known_dir, filename)
                img = cv2.imread(filepath)
                if img is not None:
                    name = os.path.splitext(filename)[0].replace("_", " ").title()
                    # Compute HSV Color Histogram as a robust template feature vector
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    hist = cv2.calcHist([hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
                    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                    self.known_face_histograms[name] = hist
                    
        print(f"[AI Analytics] Loaded {len(self.known_face_histograms)} known person profile(s): {list(self.known_face_histograms.keys())}")

    def detect_and_classify(self, frame, camera_name="Camera"):
        """
        Runs YOLOv8 detection and classifies persons as KNOWN or UNKNOWN.
        Publishes event to OSGi EventBus when an UNKNOWN person is detected.
        """
        if frame is None:
            return None, [], False

        orig_h, orig_w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame, 1.0/255.0, (config.INPUT_WIDTH, config.INPUT_HEIGHT), 
            [0, 0, 0], swapRB=True, crop=False
        )

        self.net.setInput(blob)
        outputs = self.net.forward()
        outputs = outputs.transpose((0, 2, 1))

        boxes = []
        confidences = []
        x_factor = orig_w / float(config.INPUT_WIDTH)
        y_factor = orig_h / float(config.INPUT_HEIGHT)

        for i in range(outputs[0].shape[0]):
            row = outputs[0][i]
            person_score = row[4]
            if person_score >= self.conf_threshold:
                x_c, y_c, w, h = row[0], row[1], row[2], row[3]
                left = int((x_c - w / 2.0) * x_factor)
                top = int((y_c - h / 2.0) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)

                if width > 10 and height > 10:
                    boxes.append([left, top, width, height])
                    confidences.append(float(person_score))

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)
        detections = []
        draw_frame = frame.copy()
        unknown_detected = False

        if len(indices) > 0:
            for idx in np.array(indices).flatten():
                x, y, w, h = boxes[idx]
                x, y = max(0, x), max(0, y)
                w, h = min(orig_w - x, w), min(orig_h - y, h)
                conf = confidences[idx]

                # Crop person region for classification
                person_crop = frame[y:y+h, x:x+w]
                identity, match_score = self._classify_person(person_crop)

                is_known = identity != "UNKNOWN"
                if not is_known:
                    unknown_detected = True

                detections.append({
                    "box": [x, y, w, h],
                    "confidence": conf,
                    "identity": identity,
                    "is_known": is_known
                })

                # Draw HUD bounding box
                color = (0, 255, 0) if is_known else (0, 0, 255) # Green for Known, Red for Unknown
                label = f"{identity} ({conf:.0%})" if is_known else f"UNKNOWN PERSON ({conf:.0%})"
                
                self._draw_hud_box(draw_frame, (x, y, w, h), color)

                # Label text
                (lbl_w, lbl_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                lbl_y = max(y - 8, lbl_h + 10)
                
                # Translucent overlay label
                overlay = draw_frame.copy()
                cv2.rectangle(overlay, (x, lbl_y - lbl_h - 6), (x + lbl_w + 10, lbl_y + baseline + 2), color, -1)
                cv2.addWeighted(overlay, 0.4, draw_frame, 0.6, 0, draw_frame)
                
                cv2.putText(draw_frame, label, (x + 5, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Trigger OSGi EventBus event if an Unknown Person was detected
        if unknown_detected:
            framework.event_bus.publish("UNKNOWN_PERSON_ALERT", {
                "camera": camera_name,
                "timestamp": time.strftime("%H:%M:%S"),
                "frame": frame.copy(),
                "detections": detections
            })

        return draw_frame, detections, unknown_detected

    def _classify_person(self, person_crop):
        """Compares person crop against known profile templates."""
        if person_crop is None or person_crop.size == 0 or not self.known_face_histograms:
            return "UNKNOWN", 0.0

        try:
            hsv_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
            crop_hist = cv2.calcHist([hsv_crop], [0, 1], None, [180, 256], [0, 180, 0, 256])
            cv2.normalize(crop_hist, crop_hist, 0, 1, cv2.NORM_MINMAX)

            best_match = None
            best_score = 0.0

            for name, known_hist in self.known_face_histograms.items():
                score = cv2.compareHist(known_hist, crop_hist, cv2.HISTCMP_CORREL)
                if score > best_score:
                    best_score = score
                    best_match = name

            # Threshold for positive identity match
            if best_score >= 0.65 and best_match:
                return f"KNOWN: {best_match}", best_score

        except Exception:
            pass

        return "UNKNOWN", 0.0

    def _draw_hud_box(self, img, box, color, thickness=1, corner_length=15, corner_thickness=3):
        x, y, w, h = box
        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
        cl = min(corner_length, w // 4, h // 4)
        ct = corner_thickness
        
        # Draw tech corner ticks
        cv2.line(img, (x, y), (x + cl, y), color, ct)
        cv2.line(img, (x, y), (x, y + cl), color, ct)
        cv2.line(img, (x + w, y), (x + w - cl, y), color, ct)
        cv2.line(img, (x + w, y), (x + w, y + cl), color, ct)
        cv2.line(img, (x, y + h), (x + cl, y + h), color, ct)
        cv2.line(img, (x, y + h), (x, y + h - cl), color, ct)
        cv2.line(img, (x + w, y + h), (x + w - cl, y + h), color, ct)
        cv2.line(img, (x + w, y + h), (x + w, y + h - cl), color, ct)

# Register service into OSGi framework
ai_service = AIAnalyticsService()
framework.register_service("ai_analytics_service", ai_service)
