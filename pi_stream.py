import cv2
import socket
import struct
import pickle
import time
import threading
SERVER_IP = '192.168.1.112'
PORT = 8000
INTERVAL = 2
STREAM_URL = "http://192.168.1.73:8080/video"

class FreshCamera:
    def __init__(self, url):
        self.url = url
        self.capture = cv2.VideoCapture(url)
        self.latest_frame = None
        self.status = False
        self.stopped = False
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while not self.stopped:
            if self.capture.isOpened():
                ret, frame = self.capture.read()
                if ret:
                    self.latest_frame = frame
                    self.status = True
                else:
                    self.status = False
            else:
                print("[WARN] Cam disconnected. Reopening...")
                self.capture.open(self.url)
                time.sleep(1)

    def get_frame(self):
        return self.status, self.latest_frame

    def stop(self):
        self.stopped = True
        self.capture.release()
print(f"[INFO] Connecting to Phone (Threaded Mode): {STREAM_URL}")
cam = FreshCamera(STREAM_URL)
time.sleep(2)

while True:
    try:
        ret, frame = cam.get_frame()

        if not ret or frame is None:
            print("[WARN] No frame available yet...")
            time.sleep(1)
            continue
        _, img_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        data = pickle.dumps(img_encoded, 0)
        size = len(data)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2)
            client_socket.connect((SERVER_IP, PORT))
            client_socket.sendall(struct.pack(">L", size) + data)
            client_socket.close()
            print(f"[LIVE] Snapshot sent! ({size/1024:.1f} KB)")
        except Exception as e:
            print(f"[SKIP] Laptop busy or network error: {e}")
        time.sleep(INTERVAL)
    except KeyboardInterrupt:
        cam.stop()
        break