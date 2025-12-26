import cv2
import socket
import struct
import pickle
import time
import threading
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--server_ip", type=str, required=True, help="IP of the LPR Server")
parser.add_argument("--port", type=int, default=8000, help="Port of the LPR Server")
parser.add_argument("--camera", type=str, default="0", help="Camera URL or ID")
args = parser.parse_args()
CAMERA_SOURCE = 0 if args.camera == "0" else args.camera

SERVER_IP = args.server_ip
PORT = args.port
INTERVAL = 2.0

class FreshCamera:
    def __init__(self, source):
        self.capture = cv2.VideoCapture(source)
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
                print("[WARN] Camera disconnected. Reconnecting...")
                time.sleep(1)
                self.capture.open(CAMERA_SOURCE)

    def get_frame(self):
        return self.status, self.latest_frame

    def stop(self):
        self.stopped = True
        self.capture.release()

print(f"Client Started.")
print(f"Camera: {CAMERA_SOURCE}")
print(f"Target: {SERVER_IP}:{PORT}")

cam = FreshCamera(CAMERA_SOURCE)
time.sleep(2)

while True:
    try:
        ret, frame = cam.get_frame()

        if not ret or frame is None:
            print(" No frame...")
            time.sleep(1)
            continue
        _, img_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        data = pickle.dumps(img_encoded, 0)
        size = len(data)

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)
            client_socket.connect((SERVER_IP, PORT))
            client_socket.sendall(struct.pack(">L", size) + data)
            client_socket.close()
            print(f"Snapshot ({size/1024:.1f} KB)")
        except Exception as e:
            print(f"Connect error: {e}")

        time.sleep(INTERVAL)

    except KeyboardInterrupt:
        cam.stop()
        break