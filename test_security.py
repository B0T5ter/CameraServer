import time
import unittest
from collections import deque

from auth import (
    MAX_LOGIN_ATTEMPTS,
    MAX_OTP_ATTEMPTS,
    failed_logins,
    otp_attempts,
    verification_codes,
    generate_otp_code,
    otp_is_valid,
    record_failed_login,
    clear_login_state,
    is_login_blocked,
)
from camera_engine import CameraStream, BUFFER_SECONDS, FPS, RECORD_AFTER_MOTION


class SecurityPatchTests(unittest.TestCase):
    def setUp(self):
        failed_logins.clear()
        verification_codes.clear()
        otp_attempts.clear()

    def test_otp_is_rejected_after_expiration(self):
        code = generate_otp_code()
        verification_codes["alice"] = {
            "code": code,
            "expires_at": time.time() - 1,
        }
        self.assertFalse(otp_is_valid("alice", code))

    def test_otp_is_blocked_after_too_many_invalid_codes(self):
        verification_codes["alice"] = {
            "code": "123456",
            "expires_at": time.time() + 60,
        }

        for _ in range(MAX_OTP_ATTEMPTS):
            self.assertFalse(otp_is_valid("alice", "000000"))

        self.assertNotIn("alice", verification_codes)
        self.assertFalse(otp_is_valid("alice", "123456"))

    def test_failed_login_reaches_throttle_limit(self):
        for _ in range(MAX_LOGIN_ATTEMPTS - 1):
            self.assertFalse(record_failed_login("bob"))
        self.assertTrue(record_failed_login("bob"))
        self.assertTrue(is_login_blocked("bob"))

    def test_clear_login_state_removes_otp_and_block(self):
        code = generate_otp_code()
        verification_codes["charlie"] = {
            "code": code,
            "expires_at": time.time() + 60,
        }
        failed_logins["charlie"] = [time.time()]

        clear_login_state("charlie")

        self.assertNotIn("charlie", verification_codes)
        self.assertNotIn("charlie", failed_logins)

    def test_recording_keeps_5_second_pre_roll_and_10_second_tail(self):
        cam = CameraStream.__new__(CameraStream)
        cam.recording = False
        cam.buffer = deque(maxlen=BUFFER_SECONDS * FPS)
        cam.recording_buffer = deque(maxlen=BUFFER_SECONDS * FPS)
        cam.writer = None
        cam.motion_active = False
        cam.trailing_frames_left = 0
        cam.detect_motion = lambda frame: True
        cam.start_recording = lambda: setattr(cam, "recording", True)
        cam.stop_recording = lambda: setattr(cam, "recording", False)

        # initial motion -> should start recording and set last_motion_time
        cam.process_logic(None)
        self.assertTrue(cam.recording)
        self.assertIsNotNone(cam.last_motion_time)

        # now simulate no motion and that RECORD_AFTER_MOTION seconds passed
        cam.detect_motion = lambda frame: False
        cam.last_motion_time = time.time() - (RECORD_AFTER_MOTION + 0.1)
        cam.process_logic(None)
        self.assertFalse(cam.recording)


if __name__ == "__main__":
    unittest.main()
