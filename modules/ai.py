import re
from ultralytics import YOLO
import easyocr
import config

class LPR_Engine:
    def __init__(self):
        print(f"Loading YOLO: {config.YOLO_MODEL}")
        self.detector = YOLO(config.YOLO_MODEL)
        
        print(f"Loading EasyOCR")
        self.reader = easyocr.Reader(['en'], gpu=config.USE_GPU)

    def detect_vehicle(self, frame):
        results = self.detector(frame, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf > config.CONF_THRESHOLD:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    detections.append([x1, y1, x2, y2, conf])
        return detections

    def read_text(self, image_parts):
        full_text = ""
        for part in image_parts:
            results = self.reader.readtext(part, detail=1)
            
            for (bbox, text, prob) in results:
                if prob > 0.3: 
                    full_text += text
        return full_text

    def clean_vn_plate(self, text):
        text = re.sub(r'[^A-Za-z0-9]', '', text).upper()
        to_num = {'O': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6', 'A': '4'}
        to_char = {'0': 'D', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '8': 'B', '6': 'G'}
        
        chars = list(text)
        length = len(chars)
        if length < 7 or length > 9:
            return None
        if length == 8: 
            for i in [0, 1]: 
                if chars[i] in to_num: chars[i] = to_num[chars[i]]
            if chars[2] in to_char: chars[2] = to_char[chars[2]]
            for i in range(3, 8):
                if chars[i] in to_num: chars[i] = to_num[chars[i]]
            
            final = "".join(chars)
            if re.match(r'^\d{2}[A-Z][A-Z0-9]\d{4}$', final) or re.match(r'^\d{2}[A-Z]\d{5}$', final):
                return f"{final[:3]}-{final[3:]}"
        elif length == 9:
            for i in [0, 1]: 
                if chars[i] in to_num: chars[i] = to_num[chars[i]]
            if chars[2] in to_char: chars[2] = to_char[chars[2]]
            for i in range(4, 9):
                if chars[i] in to_num: chars[i] = to_num[chars[i]]

            final = "".join(chars)
            if re.match(r'^\d{2}[A-Z][A-Z0-9]\d{5}$', final):
                return f"{final[:4]}-{final[4:]}" 

        return None