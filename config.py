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


USERS = {
    "filip": os.environ.get("USER_FILIP_PASSWORD", "changeme"),
    "marlena": os.environ.get("USER_MARLENA_PASSWORD", "changeme"),
    "grzegorz": os.environ.get("USER_GRZEGORZ_PASSWORD", "changeme")
}

USER_EMAILS = {
    "filip": os.environ.get("USER_FILIP_EMAIL", "filip@example.com"),
    "marlena": os.environ.get("USER_MARLENA_EMAIL", "marlena@example.com"),
    "grzegorz": os.environ.get("USER_GRZEGORZ_EMAIL", "grzegorz@example.com")
}

MAIL_SETTINGS = {
    "server": os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    "port": env_int("MAIL_PORT", 587),
    "user": os.environ.get("MAIL_USER", "user@example.com"),
    "password": os.environ.get("MAIL_PASSWORD", "changeme")
}

NGINX_URL = os.environ.get("NGINX_URL", "/files/")
ROOT_SAVE_DIR = os.environ.get("ROOT_SAVE_DIR", "/mnt/dysk/recording")
USER_NAME = os.environ.get("USER_NAME", "filip")
WIDTH, HEIGHT = 1280, 720
FPS = 15
BUFFER_SECONDS = 5
RECORD_AFTER_MOTION = 10
MIN_AREA = 10000
KEEP_DAYS = 30

CAM_CONFIG = [
    {
        "name": os.environ.get("CAM1_NAME", "Furtka"),
        "rtsp_url": os.environ.get("CAM1_RTSP_URL", "")
    },
    {
        "name": os.environ.get("CAM2_NAME", "Brama"),
        "rtsp_url": os.environ.get("CAM2_RTSP_URL", "")
    }
]

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
os.umask(0o000)
