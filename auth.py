from flask_login import UserMixin
import smtplib
import random
from email.mime.text import MIMEText
from config import USERS, USER_EMAILS, MAIL_SETTINGS

verification_codes = {}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def setup_login_manager(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        if user_id in USERS:
            return User(user_id)
        return None

def send_otp_mail(username):
    if username not in USER_EMAILS:
        return False
    
    target_email = USER_EMAILS[username]
    code = str(random.randint(100000, 999999))
    verification_codes[username] = code
    
    msg = MIMEText(f"Twoj kod logowania to: {code}")
    msg['Subject'] = "Kod autoryzacyjny 2FA"
    msg['From'] = MAIL_SETTINGS["user"]
    msg['To'] = target_email

    try:
        with smtplib.SMTP(MAIL_SETTINGS["server"], MAIL_SETTINGS["port"]) as server:
            server.starttls()
            server.login(MAIL_SETTINGS["user"], MAIL_SETTINGS["password"])
            server.send_message(msg)
        return True
    except Exception:
        return False
