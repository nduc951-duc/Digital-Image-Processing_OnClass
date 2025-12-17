import cv2
import socket
import struct
import pickle
import re
import os
import numpy as np
from ultralytics import YOLO
import easyocr
PORT = 8000
CONF_THRESHOLD = 0.5
SAVE_FOLDER = "captured_plates"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)
print("Loading models")
model = YOLO('raspibackup/seperatelpr/license_plate_detector.pt') 
reader = easyocr.Reader(['en'], gpu=False)
image_counter = 1

def clean_vn_plate(text):
    text = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    if len(text) < 7 or len(text) > 10: return None
    
    chars = list(text)
    dict_to_num = {'O': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6', 'A': '4'}
    dict_to_char = {'0': 'D', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '8': 'B'}
    for i in [0, 1]:
        if chars[i] in dict_to_num: chars[i] = dict_to_num[chars[i]]
    if chars[2] in dict_to_char: chars[2] = dict_to_char[chars[2]]
    for i in range(3, len(chars)):
        if chars[i] in dict_to_num: chars[i] = dict_to_num[chars[i]]
    final_text = "".join(chars)
    if re.match(r'^\d{2}[A-Z]\d{4,6}$', final_text):
        return f"{final_text[:2]}-{final_text[2:]}"
    return None

def server_loop():
    global image_counter
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PORT))
    s.listen(5)
    print(f"Ready on port {PORT}")
    print(f"check {SAVE_FOLDER} after for saved images")
    while True:
        try:
            conn, addr = s.accept()
            data = b""
            payload_size = struct.calcsize(">L")
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet: break
                data += packet
            if len(data) < payload_size: conn.close(); continue
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]
            
            while len(data) < msg_size:
                data += conn.recv(4096)
            frame_data = data[:msg_size]
            frame_pickled = pickle.loads(frame_data)
            frame = cv2.imdecode(frame_pickled, cv2.IMREAD_COLOR)
            results = model(frame, verbose=False)
            valid_detection = False
            
            for r in results:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf > CONF_THRESHOLD:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        plate_crop = frame[y1:y2, x1:x2]
                        h, w = plate_crop.shape[:2]
                        if h/w > 0.5:
                            split = h//2
                            top = reader.readtext(plate_crop[0:split, :], detail=0)
                            bot = reader.readtext(plate_crop[split:h, :], detail=0)
                            raw_text = "".join(top + bot)
                        else:
                            raw_text = "".join(reader.readtext(plate_crop, detail=0))
                        clean_text = clean_vn_plate(raw_text)
                        
                        if clean_text:
                            print(f"SAVED: {clean_text} (image_{clean_text}.png)")
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, clean_text, (x1, y1-10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                            
                            valid_detection = True

            if valid_detection:
                filename = f"{SAVE_FOLDER}/image_{clean_text}.png"
                cv2.imwrite(filename, frame)
            else:
                print(f"[LOG] Frame processed. No valid plates.")

            conn.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    server_loop()