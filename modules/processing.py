import cv2
import numpy as np

def preprocess_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    return denoised
def split_plate(plate_img):
    h, w = plate_img.shape[:2]
    ratio = h / w
    if ratio > 0.5:
        split_point = h // 2
        top_part = plate_img[0:split_point, :]
        bot_part = plate_img[split_point:h, :]
        
        return True, (top_part, bot_part)
    
    else:
        return False, [plate_img]
def draw_result(frame, text, box):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, text, (x1, y1-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame