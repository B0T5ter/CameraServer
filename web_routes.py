from flask import Response, render_template_string, request, redirect, url_for, session
from flask_login import login_user, login_required, logout_user, current_user
import shutil
import cv2
import time
from auth import User, send_otp_mail, verification_codes
from config import USERS, NGINX_URL

HTML_BASE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Monitoring</title>
    <style>
        body { margin: 0; font-family: sans-serif; background: #121212; color: #e0e0e0; }
        header { background: #1f1f1f; padding: 15px; border-bottom: 2px solid #007bff; display: flex; justify-content: space-between; align-items: center; }
        h1 { margin: 0; font-size: 1.2rem; }
        .nav-btn { background: #007bff; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; margin-left: 10px; font-size: 0.9rem; }
        .btn-logout { background: #dc3545; }
        .container { padding: 20px; text-align: center; }
        .cam-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; }
        .cam-box { background: #000; border: 1px solid #333; max-width: 640px; width: 100%; position: relative; }
        .cam-label { position: absolute; top: 0; left: 0; background: rgba(0,0,0,0.6); padding: 5px 10px; font-weight: bold; width: 100%; text-align: left; box-sizing: border-box; }
        img.stream { width: 100%; height: auto; display: block; }
        iframe { width: 100%; height: 80vh; border: none; background: #fff; border-radius: 5px; }
        .login-box { width: 300px; margin: 100px auto; background: #1f1f1f; padding: 30px; border-radius: 8px; }
        input { width: 100%; padding: 10px; margin: 10px 0; background: #333; border: 1px solid #444; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 1rem; }
    </style>
</head>
<body>
    {% if current_user.is_authenticated %}
    <header>
        <h1>System Monitoringu</h1>
        <nav>
            <a href="/" class="nav-btn">Na Zywo</a>
            <a href="/recordings" class="nav-btn">Nagrania</a>
            <a href="/logout" class="nav-btn btn-logout">Wyloguj</a>
        </nav>
    </header>
    {% endif %}
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

HTML_LOGIN = """
{% extends "base" %}
{% block content %}
<div class="login-box">
    <h2>Zaloguj sie</h2>
    <form method="post" action="/login">
        <input type="text" name="username" placeholder="Uzytkownik" required autofocus>
        <input type="password" name="password" placeholder="Haslo" required>
        <button type="submit">Wejdz</button>
    </form>
    {% if error %}
    <p style="color: #ff4444; margin-top: 10px;">{{ error }}</p>
    {% endif %}
</div>
{% endblock %}
"""

HTML_VERIFY = """
{% extends "base" %}
{% block content %}
<div class="login-box">
    <h2>Wpisz kod z maila</h2>
    <form method="post" action="/verify">
        <input type="text" name="code" placeholder="6-cyfrowy kod" required autofocus>
        <button type="submit">Weryfikuj</button>
    </form>
    {% if error %}
    <p style="color: #ff4444; margin-top: 10px;">{{ error }}</p>
    {% endif %}
</div>
{% endblock %}
"""

HTML_DASHBOARD = """
{% extends "base" %}
{% block content %}
    <div style="max-width: 800px; margin: 0 auto 20px auto; text-align: left; background: #1f1f1f; padding: 15px; border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-weight: bold; color: #007bff;">Dysk (/mnt/dysk)</span>
            <span>{{ d_used }} GB / {{ d_total }} GB ({{ d_percent }}%)</span>
        </div>
        <div style="width: 100%; background: #333; height: 10px; border-radius: 5px; overflow: hidden;">
            <div style="height: 100%; width: {{ d_percent }}%;
                        background: {% if d_percent > 90 %}#dc3545{% else %}#28a745{% endif %};">
            </div>
        </div>
    </div>
    <div class="cam-grid">
        {% for cam in cams %}
        <div class="cam-box">
            <div class="cam-label">{{ cam.name }}</div>
            <img src="/video_feed/{{ cam.name }}" class="stream">
        </div>
        {% endfor %}
    </div>
{% endblock %}
"""

HTML_RECORDINGS = """
{% extends "base" %}
{% block content %}
    <iframe src="{{ nginx_url }}"></iframe>
{% endblock %}
"""

def setup_routes(app, cameras):
    app.jinja_env.loader = None
    from jinja2 import DictLoader
    app.jinja_env.loader = DictLoader({
        'base': HTML_BASE,
        'login': HTML_LOGIN,
        'verify': HTML_VERIFY,
        'dashboard': HTML_DASHBOARD,
        'recordings': HTML_RECORDINGS
    })

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if username in USERS and USERS[username] == password:
                if send_otp_mail(username):
                    session['pending_user'] = username
                    return redirect(url_for('verify'))
                else:
                    return render_template_string(HTML_LOGIN, error="Blad systemu mailowego")
            else:
                return render_template_string(HTML_LOGIN, error="Bledny login lub haslo")
        return render_template_string(HTML_LOGIN)

    @app.route('/verify', methods=['GET', 'POST'])
    def verify():
        if 'pending_user' not in session:
            return redirect(url_for('login'))
        username = session['pending_user']
        if request.method == 'POST':
            entered_code = request.form['code']
            if username in verification_codes and verification_codes[username] == entered_code:
                login_user(User(username))
                session.pop('pending_user', None)
                if username in verification_codes:
                    del verification_codes[username]
                return redirect(url_for('index'))
            else:
                return render_template_string(HTML_VERIFY, error="Nieprawidlowy kod")
        return render_template_string(HTML_VERIFY)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def index():
        try:
            total, used, free = shutil.disk_usage("/mnt/dysk")
        except FileNotFoundError:
            total, used, free = shutil.disk_usage("/")
        d_total = round(total / (1024**3), 2)
        d_used  = round(used / (1024**3), 2)
        d_percent = round((used / total) * 100, 1)
        return render_template_string(HTML_DASHBOARD, cams=cameras, d_total=d_total, d_used=d_used, d_percent=d_percent)

    @app.route('/recordings')
    @login_required
    def recordings():
        return render_template_string(HTML_RECORDINGS, nginx_url=NGINX_URL)

    def gen_frames(cam_name):
        cam = next((c for c in cameras if c.name == cam_name), None)
        while cam:
            if cam.frame is not None:
                ret, buffer = cv2.imencode('.jpg', cam.frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)

    @app.route('/video_feed/<cam_name>')
    @login_required
    def video_feed(cam_name):
        return Response(gen_frames(cam_name), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/auth')
    def auth():
        if current_user.is_authenticated:
            return "OK", 200
        else:
            return "Unauthorized", 401
