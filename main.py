from flask import Flask
from flask_login import LoginManager
import os
import threading
from camera_engine import cameras, cleanup_old_recordings
from auth import setup_login_manager
from web_routes import setup_routes
from utils import segreguj_stare_nagrania_loop

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

setup_login_manager(login_manager)
setup_routes(app, cameras)

if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_old_recordings, daemon=True)
    cleanup_thread.start()
    
    segreg_thread = threading.Thread(target=segreguj_stare_nagrania_loop, daemon=True)
    segreg_thread.start()

    app.run(host='0.0.0.0', port=21320, threaded=True, debug=False)
