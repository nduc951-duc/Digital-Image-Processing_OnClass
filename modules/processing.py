import cv2
import numpy as np

def preprocess_for_ocr(img):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    return denoised

def deskew(img_gray):
    try:
        _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0: return img_gray
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 2:
            return img_gray
        if abs(angle) > 15:
            return img_gray

        (h, w) = img_gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        rotated = cv2.warpAffine(img_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
        
    except Exception:
        return img_gray

def find_split_point(img_gray):
    
    try:
        _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        h, w = thresh.shape
        row_sums = np.sum(thresh, axis=1)
        start = int(h * 0.30)
        end = int(h * 0.70)
        
        min_val = np.inf
        split_index = h // 2
        
        for i in range(start, end):
            if row_sums[i] < min_val:
                min_val = row_sums[i]
                split_index = i
        
        return split_index
    except:
        return img_gray.shape[0] // 2

def split_plate(plate_img):
    if len(plate_img.shape) == 3:
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_img
    processed_img = deskew(gray)

    h, w = processed_img.shape
    if h < 10 or w < 10:
        return False, []

    ratio = h / w
    
    if ratio > 0.5:
        split_point = find_split_point(processed_img)
        if split_point < 5 or split_point > h - 5:
            split_point = h // 2
        y_start = max(0, split_point - 2)
        y_end = min(h, split_point + 2)
        
        top_part = processed_img[0:y_end, :]
        bot_part = processed_img[y_start:h, :]
        
        return True, (top_part, bot_part)
    
    else:
        return False, [processed_img]

def draw_result(frame, text, box):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, text, (x1, y1-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame