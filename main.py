import socket
import struct
import pickle
import cv2
import time
import argparse
import sys
import os

from modules.ai import LPR_Engine
from modules import processing
import config 

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="0.0.0.0")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--model", type=str, default="license_plate_detector.pt")
args = parser.parse_args()

def main():
    print(f"Loading Model: {args.model}")
    engine = LPR_Engine() 
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((args.host, args.port))
    except Exception as e:
        print(f"Bind failed: {e}")
        return

    server.listen(5)
    print(f"LPR Server Online @ {args.host}:{args.port}")
    print(f"Saving cropped plates to: {config.SAVE_FOLDER}")

    while True:
        try:
            conn, addr = server.accept()
            
            data = b""
            payload_size = struct.calcsize(">L")
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet: break
                data += packet
            
            if len(data) < payload_size:
                conn.close()
                continue
                
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]
            while len(data) < msg_size:
                data += conn.recv(4096)
            
            frame_data = data[:msg_size]
            frame_pickled = pickle.loads(frame_data)
            frame = cv2.imdecode(frame_pickled, cv2.IMREAD_COLOR)
            detections = engine.detect_vehicle(frame)
            
            if not detections:
                if config.PRINT_LOGS: print("[LOG] No plates detected.")
            for i, det in enumerate(detections):
                x1, y1, x2, y2, conf = det
                plate_crop = frame[y1:y2, x1:x2]
                if plate_crop.shape[0] == 0 or plate_crop.shape[1] == 0:
                    continue
                plate_crop_processed = processing.preprocess_for_ocr(plate_crop)
                is_split, parts = processing.split_plate(plate_crop_processed)
                raw_text = engine.read_text(parts)
                clean_text = engine.clean_vn_plate(raw_text)
                if clean_text:
                    print(f"PLATE FOUND: {clean_text}")
                    frame = processing.draw_result(frame, clean_text, (x1,y1,x2,y2))
                    timestamp = int(time.time())
                    filename = f"{config.SAVE_FOLDER}/{clean_text}_{timestamp}.png"
                    if not os.path.exists(filename):
                        cv2.imwrite(filename, plate_crop)
                        print(f"SAVED {filename}")
                
                else:
                    if config.PRINT_LOGS:
                        print(f"REJECT: '{raw_text}'")

            conn.close()

        except Exception as e:
            print(f"Processing Loop: {e}")
            if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    main()