import os
from pathlib import Path


def load_dotenv(env_path: Path):
    if not env_path.exists():
        return
    with env_path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


dotenv_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path)


def env_int(key, default):
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def required_env(key):
    value = os.environ.get(key)
    if not value or value in {"changeme", "example_password", "change_this_to_a_secure_random_value", "generate_a_long_random_value"}:
        raise RuntimeError(f"Brak bezpiecznej wartosci zmiennej {key} w .env")
    return value


USERS = {
    "filip": required_env("USER_FILIP_PASSWORD"),
    "marlena": required_env("USER_MARLENA_PASSWORD"),
    "grzegorz": required_env("USER_GRZEGORZ_PASSWORD")
}

USER_EMAILS = {
    "filip": required_env("USER_FILIP_EMAIL"),
    "marlena": required_env("USER_MARLENA_EMAIL"),
    "grzegorz": required_env("USER_GRZEGORZ_EMAIL")
}

MAIL_SETTINGS = {
    "server": os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    "port": env_int("MAIL_PORT", 587),
    "user": required_env("MAIL_USER"),
    "password": required_env("MAIL_PASSWORD")
}

NGINX_URL = os.environ.get("NGINX_URL", "/files/")
ROOT_SAVE_DIR = os.environ.get("ROOT_SAVE_DIR", "/mnt/dysk/recording")
USER_NAME = os.environ.get("USER_NAME", "filip")
WIDTH, HEIGHT = 1280, 720
FPS = 15
BUFFER_SECONDS = 5
RECORD_AFTER_MOTION = 10
MIN_AREA = env_int("MOTION_MIN_AREA", 2000)
VAR_THRESHOLD = env_int("MOTION_VAR_THRESHOLD", 80)
THRESHOLD_VALUE = env_int("MOTION_THRESHOLD_VALUE", 200)
KEEP_DAYS = 30

CAM_CONFIG = [
    {
        "name": os.environ.get("CAM1_NAME", "Furtka"),
        "rtsp_url": os.environ.get("CAM1_RTSP_URL", ""),
        "recording_rtsp_url": os.environ.get("CAM1_RECORDING_RTSP_URL", os.environ.get("CAM1_RTSP_URL", ""))
    },
    {
        "name": os.environ.get("CAM2_NAME", "Brama"),
        "rtsp_url": os.environ.get("CAM2_RTSP_URL", ""),
        "recording_rtsp_url": os.environ.get("CAM2_RECORDING_RTSP_URL", os.environ.get("CAM2_RTSP_URL", ""))
    }
]

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
os.umask(0o077)
