import socket
import struct
import pickle
import cv2
import config
from modules.ai import LPR_Engine
from modules import processing

def main():
    # 1. Initialize System
    engine = LPR_Engine()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.HOST, config.PORT))
    server.listen(5)
    print(f"[SYSTEM] LPR Server Online @ {config.PORT}")
    print(f"[SYSTEM] Saving to: {config.SAVE_FOLDER}/")
    while True:
        try:
            conn, addr = server.accept()
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
            detections = engine.detect_vehicle(frame)
            
            found_valid = False
            for det in detections:
                x1, y1, x2, y2, conf = det
                plate_crop = frame[y1:y2, x1:x2]

                # 2. Pre-process
                plate_crop = processing.preprocess_for_ocr(plate_crop)

                # 3. Split Logic (Square/Long)
                is_split, parts = processing.split_plate(plate_crop)

                # 4. Read Text
                raw_text = engine.read_text(parts)
                
                # 5. Clean Logic
                clean_text = engine.clean_vn_plate(raw_text)

                if clean_text:
                    print(f"PLATE: {clean_text}")
                    frame = processing.draw_result(frame, clean_text, (x1,y1,x2,y2))
                    found_valid = True
                else:
                    if config.PRINT_LOGS:
                        print(f"Rejected: {raw_text}")
            if found_valid:
                filename = f"{config.SAVE_FOLDER}/plate_{clean_text}.png"
                cv2.imwrite(filename, frame)
            
            # if config.SHOW_WINDOW:
            #     cv2.imshow("Professional LPR", frame)
            #     if cv2.waitKey(1) == ord('q'): break

            conn.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    main()