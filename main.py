from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import threading
from camera_engine import build_cameras, cleanup_old_recordings
from auth import setup_login_manager
from config import required_env
from web_routes import setup_routes
from utils import segreguj_stare_nagrania_loop

secret_key = required_env("SECRET_KEY")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SECURE=True,
    REMEMBER_COOKIE_SAMESITE="Lax",
    PREFERRED_URL_SCHEME="https"
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

setup_login_manager(login_manager)
app_cameras = build_cameras()
setup_routes(app, app_cameras)

@app.after_request
def add_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
    return response

if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_old_recordings, daemon=True)
    cleanup_thread.start()

    segreg_thread = threading.Thread(target=segreguj_stare_nagrania_loop, daemon=True)
    segreg_thread.start()

    app.run(host='127.0.0.1', port=21320, threaded=True, debug=False)
