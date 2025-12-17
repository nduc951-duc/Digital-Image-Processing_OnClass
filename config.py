import os

PORT = 8000
HOST = '0.0.0.0'

YOLO_MODEL = 'license_plate_detector.pt'
CONF_THRESHOLD = 0.5
USE_GPU = True

SAVE_FOLDER = "captured_plates"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

SHOW_WINDOW = True 
PRINT_LOGS = True