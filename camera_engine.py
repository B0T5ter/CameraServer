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
        self.url = config.get("rtsp_url", "")
        self.recording_url = config.get("recording_rtsp_url") or self.url
        self.root_dir = ROOT_SAVE_DIR
        self.frame = None
        self.recording = False
        self.buffer = deque(maxlen=BUFFER_SECONDS * FPS)
        self.recording_buffer = deque(maxlen=BUFFER_SECONDS * FPS)
        self.writer = None
        self.video_file_path = None
        self.frames_left = 0
        self.motion_active = False
        self.trailing_frames_left = 0
        self.last_motion_time = None
        from config import VAR_THRESHOLD
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=VAR_THRESHOLD, detectShadows=False
        )
        self.frame_counter = 0
        self.cap = None
        if self.url:
            try:
                self.cap = cv2.VideoCapture(self.url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                self.cap = None
        self.recording_cap = None
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def _ensure_recording_cap(self):
        if not self.recording_url:
            return None
        if self.recording_cap is None or not self.recording_cap.isOpened():
            self.recording_cap = cv2.VideoCapture(self.recording_url)
            self.recording_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return self.recording_cap

    def update(self):
        while True:
            if self.cap is None:
                time.sleep(5)
                continue
            if not self.cap.isOpened():
                time.sleep(5)
                try:
                    self.cap.open(self.url)
                except Exception:
                    pass
                continue
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                time.sleep(1)
                continue
            frame_resized = cv2.resize(frame, (WIDTH, HEIGHT))
            self.frame = frame_resized.copy()
            self.frame_counter += 1

            # Read recording stream each loop so recording_buffer always has pre-roll frames
            recording_cap = self._ensure_recording_cap()
            if recording_cap is not None and recording_cap.isOpened():
                try:
                    rec_ret, rec_frame = recording_cap.read()
                except Exception:
                    rec_ret = False
                    rec_frame = None
                if rec_ret and rec_frame is not None:
                    rec_frame_resized = cv2.resize(rec_frame, (WIDTH, HEIGHT))
                    self.recording_buffer.append(rec_frame_resized)
                    if self.recording and self.writer:
                        self.writer.write(rec_frame_resized)
                else:
                    recording_cap.release()
                    self.recording_cap = None

            # Only run detection logic on a subset of frames to save CPU
            if self.frame_counter % 3 != 0:
                self.buffer.append(frame_resized)
                continue
            self.process_logic(frame_resized)

    def process_logic(self, frame):
        self.buffer.append(frame)
        motion_detected = self.detect_motion(frame)

        now = time.time()
        if motion_detected:
            self.last_motion_time = now
            if not self.recording:
                self.start_recording()
            return

        # no motion detected
        if self.recording:
            if self.last_motion_time is None:
                # safety: stop if we have no record of motion
                self.stop_recording()
                return
            # stop after RECORD_AFTER_MOTION seconds since last motion
            if now - self.last_motion_time >= RECORD_AFTER_MOTION:
                self.stop_recording()

    def detect_motion(self, frame):
        blurred = cv2.GaussianBlur(frame, (21, 21), 0)
        fg_mask = self.bg_subtractor.apply(blurred)
        from config import THRESHOLD_VALUE, MIN_AREA
        _, thresh = cv2.threshold(fg_mask, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
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
        writer_candidates = [
            (filename, cv2.VideoWriter_fourcc(*'VP80')),
            (os.path.join(path, f"motion_{ts}.mp4"), cv2.VideoWriter_fourcc(*'mp4v')),
            (os.path.join(path, f"motion_{ts}.avi"), cv2.VideoWriter_fourcc(*'MJPG')),
        ]
        self.writer = None
        self.video_file_path = None
        for candidate_path, fourcc in writer_candidates:
            writer = cv2.VideoWriter(candidate_path, fourcc, FPS, (WIDTH, HEIGHT))
            if writer.isOpened():
                self.writer = writer
                self.video_file_path = candidate_path
                break
        if self.writer is None:
            self.recording = False
            return
        for f in self.recording_buffer:
            self.writer.write(f)

    def stop_recording(self):
        self.recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
        if self.recording_cap is not None and self.recording_cap.isOpened():
            self.recording_cap.release()
            self.recording_cap = None
        self.recording_buffer.clear()

cameras = []


def build_cameras():
    created = []
    for cfg in CAM_CONFIG:
        try:
            created.append(CameraStream(cfg))
        except Exception:
            continue
    return created
