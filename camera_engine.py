import cv2
import os
import time
import threading
from collections import deque
from datetime import datetime
import shutil
from config import ROOT_SAVE_DIR, WIDTH, HEIGHT, FPS, BUFFER_SECONDS, RECORD_AFTER_MOTION, MIN_AREA, KEEP_DAYS, CAM_CONFIG

def cleanup_old_recordings():
    while True:
        try:
            now = datetime.now()
            if os.path.exists(ROOT_SAVE_DIR):
                for folder_name in os.listdir(ROOT_SAVE_DIR):
                    folder_path = os.path.join(ROOT_SAVE_DIR, folder_name)
                    if os.path.isdir(folder_path):
                        try:
                            folder_date = datetime.strptime(folder_name, "%Y-%m-%d")
                            days_old = (now - folder_date).days
                            if days_old > KEEP_DAYS:
                                shutil.rmtree(folder_path)
                        except ValueError:
                            pass
        except Exception:
            pass
        time.sleep(12 * 3600)

class CameraStream:
    def __init__(self, config):
        self.name = config["name"]
        self.url = config["rtsp_url"]
        self.root_dir = ROOT_SAVE_DIR
        self.frame = None
        self.recording = False
        self.buffer = deque(maxlen=BUFFER_SECONDS * FPS)
        self.writer = None
        self.video_file_path = None
        self.frames_left = 0
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=120, detectShadows=False
        )
        self.frame_counter = 0
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while True:
            if not self.cap.isOpened():
                time.sleep(5)
                self.cap.open(self.url)
                continue
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                time.sleep(1)
                continue
            frame_resized = cv2.resize(frame, (WIDTH, HEIGHT))
            self.frame = frame_resized.copy()
            self.frame_counter += 1
            if self.frame_counter % 3 != 0:
                if self.recording and self.writer:
                    self.writer.write(frame_resized)
                self.buffer.append(frame_resized)
                continue
            self.process_logic(frame_resized)

    def process_logic(self, frame):
        self.buffer.append(frame)
        if self.detect_motion(frame):
            self.frames_left = RECORD_AFTER_MOTION * FPS
            if not self.recording:
                self.start_recording()
        if self.recording:
            if self.writer:
                self.writer.write(frame)
            self.frames_left -= 3
            if self.frames_left <= 0:
                self.stop_recording()

    def detect_motion(self, frame):
        blurred = cv2.GaussianBlur(frame, (21, 21), 0)
        fg_mask = self.bg_subtractor.apply(blurred)
        _, thresh = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) > MIN_AREA:
                return True
        return False

    def start_recording(self):
        self.recording = True
        now = datetime.now()
        path = os.path.join(self.root_dir, now.strftime("%Y-%m-%d"), self.name, now.strftime("%H"))
        os.makedirs(path, exist_ok=True)
        ts = now.strftime("%H-%M-%S")
        filename = os.path.join(path, f"motion_{ts}.webm")
        self.video_file_path = filename
        self.writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'VP80'), FPS, (WIDTH, HEIGHT))
        for f in self.buffer:
            self.writer.write(f)

    def stop_recording(self):
        self.recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
            # Usunąć nagrania które trwają dokładnie 15 sekund (kamera się wyłączyła)
            if self.video_file_path and os.path.exists(self.video_file_path):
                try:
                    cap = cv2.VideoCapture(self.video_file_path)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration_seconds = frame_count / FPS if FPS > 0 else 0
                    cap.release()
                    if duration_seconds == 15:
                        os.remove(self.video_file_path)
                except Exception:
                    pass

cameras = [CameraStream(cfg) for cfg in CAM_CONFIG]
