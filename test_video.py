import cv2
import sys
import os
import config
from modules.ai import LPR_Engine
from modules import processing
from modules.tracker import Tracker

def main():
    # Handle file input from Launcher or command line
    video_path = sys.argv[1] if len(sys.argv) > 1 else "sample.mp4"
    if not os.path.exists(video_path):
        print(f"[ERROR] File not found: {video_path}")
        return

    engine = LPR_Engine()
    # Lower max_lost for video files so we don't track ghosts too long
    tracker = Tracker(max_lost=10) 
    cap = cv2.VideoCapture(video_path)

    print(f"[TEST] Processing: {video_path}")


    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.resize(frame, (1020, 600))

        # 1. Detect
        detections = engine.detect_vehicle(frame)
        
        # 2. Track & Get candidates for OCR
        active_tracks, crops_to_process = tracker.update(detections, frame)

        # 3. Draw Active Tracks (Yellow)
        for obj_id, (rect, _, _, conf) in active_tracks.items():
            x1, y1, x2, y2 = rect
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, f"ID {obj_id}", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        for (obj_id, plate_crop) in crops_to_process:
            if plate_crop.size == 0: continue
            processed_crop = processing.preprocess_for_ocr(plate_crop)
            is_split, parts = processing.split_plate(processed_crop)
            raw_text = engine.read_text(parts)
            clean_text = engine.clean_vn_plate(raw_text)
            if clean_text:
                print(f"[SUCCESS] ID {obj_id}: {clean_text}")
                tracker.set_identified(obj_id) # Stop processing this car!
                
                # Visual Feedback
                cv2.rectangle(frame, (0,0), (400, 60), (0,0,0), -1)
                cv2.putText(frame, f"FOUND: {clean_text}", (10, 45), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            else:
                # If raw_text is not empty, print it so we can fix the regex later
                if len(raw_text.strip()) > 3:
                     print(f"[REJECT] ID {obj_id} Raw: '{raw_text}'")

        cv2.imshow("CPU Optimized Test", frame)
        if cv2.waitKey(1) == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()