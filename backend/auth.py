"""Password hashing, JWT, aur 'current user' (har request par DB se fresh)."""
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from passlib.context import CryptContext

from database import fetch_one

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))

if len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET kamzor ya missing hai (kam se kam 32 characters chahiye). "
        'Banao: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# User na mile tab bhi hash verify chalate hain, taaki response time se username ka pata na chale
_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing")

USER_SQL = """
SELECT u.id AS user_id, u.username, u.password_hash, u.role, u.student_id, u.faculty_id,
       u.is_locked, COALESCE(s.department_id, f.department_id) AS department_id
FROM users u
LEFT JOIN students s ON s.student_id = u.student_id
LEFT JOIN faculty  f ON f.faculty_id = u.faculty_id
WHERE {where}
"""


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_or_dummy(plain: str, hashed):
    """hashed None ho to bhi utna hi time lagta hai."""
    if hashed is None:
        pwd_context.verify(plain, _DUMMY_HASH)
        return False
    return pwd_context.verify(plain, hashed)


def get_user_by_username(username: str):
    return fetch_one(USER_SQL.format(where="u.username = %s"), (username,))


def get_user_by_id(user_id: int):
    return fetch_one(USER_SQL.format(where="u.id = %s"), (user_id,))


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "student_id": user["student_id"],
        "faculty_id": user["faculty_id"],
        "department_id": user["department_id"],
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Token sirf 'kaun hai' batata hai. Role, ID aur is_locked HAMESHA DB se fresh padhte hain,
    taaki lock ya role badalne ka asar turant ho (purane token se bypass na ho).
    Policy engine ko yahi dict milta hai (password_hash hata ke).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    claims = decode_access_token(authorization.split(" ", 1)[1])
    if not claims or "user_id" not in claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(claims["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user.pop("password_hash", None)
    user["is_locked"] = bool(user["is_locked"])
    return user
