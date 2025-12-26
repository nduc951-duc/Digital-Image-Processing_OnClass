import os
import json
SETTINGS_FILE = 'settings.json'
defaults = {
    "yolo_model": "license_plate_detector.pt",
    "conf_threshold": 0.5,
    "host_ip": "0.0.0.0",
    "save_folder": "captured_plates"
}

if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, 'r') as f:
            user_settings = json.load(f)
            settings = {**defaults, **user_settings}
    except Exception as e:
        print(f"[WARN] Could not load settings.json: {e}")
        settings = defaults
else:
    settings = defaults
PORT = 8000
HOST = settings["host_ip"]
YOLO_MODEL = settings["yolo_model"]
CONF_THRESHOLD = float(settings["conf_threshold"]) 
SAVE_FOLDER = settings["save_folder"]

USE_GPU = True
SHOW_WINDOW = True 
PRINT_LOGS = True

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)