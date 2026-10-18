"""
Nirantar Phase 7 Authentication & Authorization Module
JWT cookie session handling, bcrypt hashing, rate limiting, and role-based route guards.
"""
import os
import time
from datetime import datetime, timedelta
import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "nirantar_secret_key_minimum_32_chars_long_2026_jwt_token!")
INVITE_CODE = os.getenv("INVITE_CODE", "NIRANTAR_FIELD_2026")
MANAGER_INVITE_CODE = os.getenv("MANAGER_INVITE_CODE", "NIRANTAR_MGR_2026")

VALID_ROLES = {"program_manager", "coordinator", "care_worker", "supervisor", "doctor"}
MANAGER_ROLES = {"program_manager", "coordinator"}
FIELD_ROLES = {"care_worker", "supervisor", "doctor"}

# Rate limiting storage: (email.lower(), client_ip) -> list of failure timestamps
_failed_logins = {}
MAX_FAILED_ATTEMPTS = 10
LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 minutes

def is_rate_limited(email, ip):
    key = (email.strip().lower(), ip)
    now = time.time()
    failures = _failed_logins.get(key, [])
    # Keep only failures within window
    failures = [t for t in failures if now - t < LOCKOUT_WINDOW_SECONDS]
    _failed_logins[key] = failures
    return len(failures) >= MAX_FAILED_ATTEMPTS

def record_login_failure(email, ip):
    key = (email.strip().lower(), ip)
    now = time.time()
    failures = _failed_logins.get(key, [])
    failures = [t for t in failures if now - t < LOCKOUT_WINDOW_SECONDS]
    failures.append(now)
    _failed_logins[key] = failures

def clear_login_failures(email, ip):
    key = (email.strip().lower(), ip)
    _failed_logins.pop(key, None)

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password, password_hash):
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

def create_session_token(user_id, role, email, name):
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=8)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_session_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

def extract_cookie_token(cookie_header):
    if not cookie_header:
        return None
    cookies = {}
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies.get("nirantar_session")

def sanitize_user(user_doc):
    """
    Strips sensitive fields like password_hash from user responses.
    """
    if not user_doc:
        return None
    clean = dict(user_doc)
    clean.pop("password_hash", None)
    clean["id"] = clean.get("id") or clean.get("_id")
    if "_id" in clean:
        clean["_id"] = str(clean["_id"])
    return clean
