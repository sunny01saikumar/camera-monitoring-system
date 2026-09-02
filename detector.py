import cv2
import numpy as np
import config

class PersonDetector:
    def __init__(self, model_path=None, conf_threshold=None, nms_threshold=None):
        self.model_path = model_path or config.MODEL_PATH
        self.conf_threshold = conf_threshold or config.DEFAULT_CONF_THRESHOLD
        self.nms_threshold = nms_threshold or config.DEFAULT_NMS_THRESHOLD
        
        # Load the ONNX network
        print(f"Loading YOLOv8 model from {self.model_path}...")
        self.net = cv2.dnn.readNet(self.model_path)
        
        # Set preferable backend and target to run faster if GPU is available
        # Default to CPU since we don't know the user's GPU setup
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        
        # COCO class name for index 0 is 'person'
        self.target_class_id = 0 

    def set_thresholds(self, conf, nms):
        """Update detection thresholds on the fly."""
        self.conf_threshold = conf
        self.nms_threshold = nms

    def detect(self, frame):
        """
        Run YOLOv8 inference on the frame and filter for persons.
        Returns:
            processed_frame: The frame with overlay bounding boxes and HUD text
            detections: List of dicts containing box coordinates and confidence
        """
        if frame is None:
            return None, []

        orig_h, orig_w = frame.shape[:2]

        # Prepare YOLOv8 input blob: resize to 640x640, scale pixels by 1/255, swap R&B channels
        blob = cv2.dnn.blobFromImage(
            frame, 
            scalefactor=1.0/255.0, 
            size=(config.INPUT_WIDTH, config.INPUT_HEIGHT), 
            mean=[0, 0, 0], 
            swapRB=True, 
            crop=False
        )

        self.net.setInput(blob)
        outputs = self.net.forward()

        # YOLOv8 raw output shape is (1, 84, 8400)
        # Transpose it to (1, 8400, 84) to iterate over detections
        outputs = outputs.transpose((0, 2, 1))
        
        boxes = []
        confidences = []
        
        x_factor = orig_w / float(config.INPUT_WIDTH)
        y_factor = orig_h / float(config.INPUT_HEIGHT)

        # Iterate over detections (8400 proposals)
        # We only check target_class_id (class 0 = person) at column index 4 of the outputs[0][i] array
        # YOLOv8 output columns: 0,1,2,3 are x,y,w,h, and 4 is 'person' confidence in COCO
        for i in range(outputs[0].shape[0]):
            row = outputs[0][i]
            person_score = row[4] # class 0 (person) score
            
            if person_score >= self.conf_threshold:
                # x_center, y_center, w, h
                x_center, y_center, w, h = row[0], row[1], row[2], row[3]
                
                # Convert center coordinates to top-left corner coordinates and scale back to original size
                left = int((x_center - w / 2.0) * x_factor)
                top = int((y_center - h / 2.0) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)
                
                # Filter invalid small/large boxes
                if width > 5 and height > 5:
                    boxes.append([left, top, width, height])
                    confidences.append(float(person_score))

        # Apply Non-Maximum Suppression (NMS) to eliminate redundant overlapping boxes
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)
        
        detections = []
        draw_frame = frame.copy()
        
        # High-tech cyber-neon colors (BGR format)
        neon_cyan = (255, 255, 0)
        neon_purple = (255, 0, 180)
        
        if len(indices) > 0:
            for idx in np.array(indices).flatten():
                box = boxes[idx]
                conf = confidences[idx]
                
                # Crop bounding box boundaries to frame limits
                x, y, w, h = box
                x = max(0, x)
                y = max(0, y)
                w = min(orig_w - x, w)
                h = min(orig_h - y, h)
                
                detections.append({
                    "box": [x, y, w, h],
                    "confidence": conf
                })
                
                # Draw the HUD style box
                self._draw_hud_box(draw_frame, (x, y, w, h), neon_cyan)
                
                # Draw a sleek translucent label
                label_text = f"PERSON: {conf:.0%}"
                (lbl_w, lbl_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                
                # Determine label Y placement to avoid frame boundary cuts
                lbl_y = y - 10 if y - 25 > 0 else y + lbl_h + 10
                lbl_x = x
                
                # Drawing transparent label background
                overlay = draw_frame.copy()
                cv2.rectangle(
                    overlay, 
                    (lbl_x, lbl_y - lbl_h - 6), 
                    (lbl_x + lbl_w + 10, lbl_y + baseline + 2), 
                    neon_cyan, 
                    -1
                )
                cv2.addWeighted(overlay, 0.35, draw_frame, 0.65, 0, draw_frame)
                
                # Text text label
                cv2.putText(
                    draw_frame, 
                    label_text, 
                    (lbl_x + 5, lbl_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.4, 
                    (255, 255, 255), 
                    1, 
                    cv2.LINE_AA
                )
                
        # Draw status overlay on the top left
        person_count = len(detections)
        status_bg = draw_frame.copy()
        cv2.rectangle(status_bg, (10, 10), (180, 50), (0, 0, 0), -1)
        cv2.addWeighted(status_bg, 0.6, draw_frame, 0.4, 0, draw_frame)
        
        cv2.putText(
            draw_frame, 
            f"LIVE TRACKING", 
            (20, 26), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            (150, 150, 150), 
            1, 
            cv2.LINE_AA
        )
        cv2.putText(
            draw_frame, 
            f"PEOPLE COUNT: {person_count}", 
            (20, 42), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
            neon_purple if person_count > 0 else (0, 255, 0), 
            1, 
            cv2.LINE_AA
        )

        return draw_frame, detections

    def _draw_hud_box(self, img, box, color, thickness=1, corner_length=15, corner_thickness=3):
        """Draws a beautiful high-tech HUD-style box with corner ticks."""
        x, y, w, h = box
        
        # Draw thin bounding box
        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
        
        # Corner configurations
        cl = min(corner_length, w // 4, h // 4)
        ct = corner_thickness
        
        # Top-Left corner
        cv2.line(img, (x, y), (x + cl, y), color, ct)
        cv2.line(img, (x, y), (x, y + cl), color, ct)
        
        # Top-Right corner
        cv2.line(img, (x + w, y), (x + w - cl, y), color, ct)
        cv2.line(img, (x + w, y), (x + w, y + cl), color, ct)
        
        # Bottom-Left corner
        cv2.line(img, (x, y + h), (x + cl, y + h), color, ct)
        cv2.line(img, (x, y + h), (x, y + h - cl), color, ct)
        
        # Bottom-Right corner
        cv2.line(img, (x + w, y + h), (x + w - cl, y + h), color, ct)
        cv2.line(img, (x + w, y + h), (x + w, y + h - cl), color, ct)
