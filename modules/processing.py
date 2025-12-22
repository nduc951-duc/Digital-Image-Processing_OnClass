import cv2
import numpy as np

def preprocess_for_ocr(img):
    # Giữ nguyên bước xử lý cơ bản này
    # Nếu ảnh vào là màu thì chuyển xám, nếu xám rồi thì thôi
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    return denoised

def deskew(img_gray):
    """
    Tính năng 1: Xoay thẳng biển số nếu bị nghiêng
    """
    # Tạo ảnh nhị phân tạm thời để tìm góc nghiêng
    _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Tìm các điểm trắng (chữ)
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0: return img_gray
    
    # Tìm khung bao quanh nghiêng (Rotated Rect)
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Chỉ xoay nếu nghiêng > 1 độ
    if abs(angle) < 1:
        return img_gray

    (h, w) = img_gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Xoay ảnh (dùng borderReplicate để lấp đầy viền đen khi xoay)
    rotated = cv2.warpAffine(img_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def find_split_point(img_gray):
    """
    Tính năng 2: Tìm khe hở giữa 2 dòng (Smart Split)
    """
    # Tạo ảnh nhị phân tạm thời chỉ để đếm pixel, KHÔNG trả về ảnh này
    _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    h, w = thresh.shape
    row_sums = np.sum(thresh, axis=1) # Đếm pixel trắng theo dòng
    
    start = int(h * 0.3)
    end = int(h * 0.7)
    
    min_val = np.inf
    split_index = h // 2
    
    # Tìm dòng có ít pixel trắng nhất (khe hở)
    for i in range(start, end):
        if row_sums[i] < min_val:
            min_val = row_sums[i]
            split_index = i
            
    return split_index

def split_plate(plate_img):
    # 1. Đảm bảo ảnh xám
    if len(plate_img.shape) == 3:
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_img

    # 2. Xoay thẳng ảnh trước (Quan trọng!)
    # Ảnh sau khi xoay vẫn là ảnh Xám (Grayscale), giữ nguyên chi tiết
    processed_img = deskew(gray)

    h, w = processed_img.shape
    ratio = h / w
    
    if ratio > 0.5: # Biển vuông
        # 3. Tìm vị trí cắt thông minh trên ảnh đã xoay
        split_point = find_split_point(processed_img)
        
        # 4. Cắt ảnh
        # Thêm margin nhỏ (2px) để không cắt phạm vào chữ
        # Output vẫn là ảnh Xám, EasyOCR rất thích điều này
        top_part = processed_img[0:split_point+2, :]
        bot_part = processed_img[split_point-2:h, :]
        
        return True, (top_part, bot_part)
    
    else:
        # Biển dài: Trả về ảnh đã xoay thẳng
        return False, [processed_img]

def draw_result(frame, text, box):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, text, (x1, y1-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame
