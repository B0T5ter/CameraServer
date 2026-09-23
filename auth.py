from flask_login import UserMixin
import smtplib
import hmac
import secrets
import time
from collections import defaultdict
from email.mime.text import MIMEText
from config import USERS, USER_EMAILS, MAIL_SETTINGS

OTP_TTL_SECONDS = 300
MAX_LOGIN_ATTEMPTS = 5
LOGIN_BAN_SECONDS = 600
MAX_OTP_ATTEMPTS = 5

verification_codes = {}
failed_logins = defaultdict(list)
otp_attempts = defaultdict(int)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def setup_login_manager(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        if user_id in USERS:
            return User(user_id)
        return None

def generate_otp_code():
    return str(secrets.randbelow(900000) + 100000)


def otp_is_valid(username, code):
    if is_otp_blocked(username):
        return False
    entry = verification_codes.get(username)
    if not entry:
        return False
    if time.time() > entry["expires_at"]:
        verification_codes.pop(username, None)
        return False
    if hmac.compare_digest(entry["code"], str(code)):
        otp_attempts.pop(username, None)
        return True

    otp_attempts[username] += 1
    if otp_attempts[username] >= MAX_OTP_ATTEMPTS:
        verification_codes.pop(username, None)
    return False


def is_otp_blocked(username):
    return otp_attempts.get(username, 0) >= MAX_OTP_ATTEMPTS


def is_login_blocked(username):
    now = time.time()
    previous_attempts = failed_logins.get(username)
    if not previous_attempts:
        return False
    attempts = [ts for ts in previous_attempts if now - ts < LOGIN_BAN_SECONDS]
    failed_logins[username] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_failed_login(username):
    failed_logins[username].append(time.time())
    attempts = [ts for ts in failed_logins.get(username, []) if time.time() - ts < LOGIN_BAN_SECONDS]
    failed_logins[username] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def clear_login_state(username):
    failed_logins.pop(username, None)
    verification_codes.pop(username, None)
    otp_attempts.pop(username, None)


def send_otp_mail(username):
    if username not in USER_EMAILS:
        return False

    target_email = USER_EMAILS[username]
    code = generate_otp_code()
    otp_attempts.pop(username, None)
    verification_codes[username] = {
        "code": code,
        "expires_at": time.time() + OTP_TTL_SECONDS,
    }

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
        verification_codes.pop(username, None)
        return False
