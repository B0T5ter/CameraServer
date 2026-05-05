# CameraServer

A simple camera monitoring system built with Flask, OpenCV, and RTSP. The application supports user login with email-based 2FA, live camera streams, motion-triggered recording, and a web interface for browsing recordings.

## Features

- user login with passwords
- email-based 2FA using a one-time code
- RTSP live camera streaming
- motion detection and automatic recording to WEBM
- recordings organized by date and hour
- automatic cleanup of old recordings after `KEEP_DAYS`

## Repository Structure

- `main.py` — application entry point
- `config.py` — configuration loading and `.env` support
- `auth.py` — authentication and 2FA email delivery
- `web_routes.py` — Flask routes and web pages
- `camera_engine.py` — camera handling, motion detection, and recording
- `utils.py` — helper utilities for cleanup and file organization
- `setup.sh` — example startup script
- `.env.example` — sample environment file

## Configuration

Sensitive values are stored in `.env` instead of hardcoding them in the code.

1. Copy the example file:

```bash
cp .env.example .env
```

2. Fill in the values in `.env`:
   - `SECRET_KEY` — secure Flask session key
   - `MAIL_*` — SMTP account settings
   - `USER_*` — user passwords and email addresses
   - `CAM*_RTSP_URL` — RTSP URLs for cameras
   - `NGINX_URL`, `ROOT_SAVE_DIR`, `USER_NAME` — environment-specific settings

## Running the Application

1. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install flask flask-login opencv-python
```

3. Start the app:

```bash
python main.py
```

4. Open your browser and go to:

```
http://0.0.0.0:21320
```

## Important Notes

- `.env` is ignored by `.gitignore` and must not be committed.
- Only `.env.example` should be kept in the repository as a template.
- If you run this on Linux, ensure the recording directory in `ROOT_SAVE_DIR` has proper permissions.
- If this repository has already been published, verify that sensitive data is not present in previous Git commits.

## Notes

- `camera_engine.py` saves recordings in the folder structure `YYYY-MM-DD/<camera>/<hour>`.
- `auth.py` sends a 2FA code to the user email addresses defined in `USER_EMAILS`.
- `main.py` uses the `SECRET_KEY` from `.env` or generates a random one if missing.

---

If you want, I can also add a `requirements.txt` or help create a simple Dockerfile.