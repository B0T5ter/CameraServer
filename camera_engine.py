import cv2
import os
import time
import threading
from collections import deque
from datetime import datetime
import shutil
from config import (
    ROOT_SAVE_DIR, WIDTH, HEIGHT, FPS, BUFFER_SECONDS, RECORD_AFTER_MOTION,
    MIN_AREA, KEEP_DAYS, CAM_CONFIG, MIN_FREE_DISK_PERCENT,
    TARGET_FREE_DISK_PERCENT, CLEANUP_INTERVAL_HOURS, MIN_RECORDING_AGE_SECONDS,
    OBJECT_DETECTION_ENABLED, OBJECT_MODEL,
    OBJECT_CONFIDENCE, OBJECT_DETECTION_INTERVAL, OBJECT_CONFIRMATION_FRAMES,
    MOTION_FALLBACK_ENABLED, DETECTION_CLASSES,
)

ACTIVE_RECORDINGS = set()
ACTIVE_RECORDINGS_LOCK = threading.Lock()
VIDEO_SUFFIXES = (".webm", ".mp4", ".avi", ".mkv", ".mov")


def cleanup_recordings_once():
    if not os.path.isdir(ROOT_SAVE_DIR):
        return 0

    now = time.time()
    candidates = []
    deleted_count = 0
    with ACTIVE_RECORDINGS_LOCK:
        active_paths = set(ACTIVE_RECORDINGS)

    for current_root, _, file_names in os.walk(ROOT_SAVE_DIR):
        for file_name in file_names:
            path = os.path.join(current_root, file_name)
            if not file_name.lower().endswith(VIDEO_SUFFIXES) or path in active_paths:
                continue
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue
            if now - stat.st_mtime < MIN_RECORDING_AGE_SECONDS:
                continue
            candidates.append((stat.st_mtime, path))

    candidates.sort()
    for _, path in candidates:
        try:
            relative_path = os.path.relpath(path, ROOT_SAVE_DIR)
            date_part = relative_path.split(os.sep, 1)[0]
            try:
                is_expired = (datetime.now() - datetime.strptime(date_part, "%Y-%m-%d")).days > KEEP_DAYS
            except ValueError:
                is_expired = False
            usage = shutil.disk_usage(ROOT_SAVE_DIR)
            free_percent = usage.free / usage.total * 100 if usage.total else 100
            if not is_expired and free_percent >= MIN_FREE_DISK_PERCENT:
                continue
            os.remove(path)
            deleted_count += 1
            usage = shutil.disk_usage(ROOT_SAVE_DIR)
            free_percent = usage.free / usage.total * 100 if usage.total else 100
            if free_percent >= TARGET_FREE_DISK_PERCENT and not is_expired:
                break
        except (FileNotFoundError, OSError):
            continue

    for current_root, directory_names, _ in os.walk(ROOT_SAVE_DIR, topdown=False):
        for directory_name in directory_names:
            try:
                os.rmdir(os.path.join(current_root, directory_name))
            except OSError:
                pass
    return deleted_count


def cleanup_old_recordings():
    while True:
        try:
            cleanup_recordings_once()
        except Exception:
            pass
        time.sleep(max(60, CLEANUP_INTERVAL_HOURS * 3600))

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
        self.object_detector = None
        self.object_detector_failed = False
        self.object_detection_counter = 0
        self.object_detection_hits = 0
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def _ensure_object_detector(self):
        if not OBJECT_DETECTION_ENABLED or self.object_detector_failed:
            return None
        if self.object_detector is None:
            try:
                from ultralytics import YOLO
                self.object_detector = YOLO(OBJECT_MODEL)
            except Exception:
                self.object_detector_failed = True
        return self.object_detector

    def detect_objects(self, frame):
        detector = self._ensure_object_detector()
        if detector is None:
            return False
        self.object_detection_counter += 1
        if self.object_detection_counter % max(1, OBJECT_DETECTION_INTERVAL) != 0:
            return self.object_detection_hits >= OBJECT_CONFIRMATION_FRAMES
        try:
            results = detector.predict(
                frame,
                conf=OBJECT_CONFIDENCE,
                classes=None,
                verbose=False,
                imgsz=640,
            )
            detected = set()
            for result in results:
                names = result.names
                for class_id in result.boxes.cls.tolist():
                    label = names[int(class_id)]
                    if label in DETECTION_CLASSES:
                        detected.add(label)
            if detected:
                self.object_detection_hits += 1
            else:
                self.object_detection_hits = 0
            return self.object_detection_hits >= max(1, OBJECT_CONFIRMATION_FRAMES)
        except Exception:
            self.object_detector_failed = True
            return False

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
        object_detected = self.detect_objects(frame)
        if self.object_detector is not None and not self.object_detector_failed:
            motion_detected = object_detected
        else:
            motion_detected = MOTION_FALLBACK_ENABLED and self.detect_motion(frame)

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
                with ACTIVE_RECORDINGS_LOCK:
                    ACTIVE_RECORDINGS.add(candidate_path)
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
        if self.video_file_path:
            with ACTIVE_RECORDINGS_LOCK:
                ACTIVE_RECORDINGS.discard(self.video_file_path)
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
