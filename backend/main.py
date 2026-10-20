import os
import sys
import time
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "policy_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "injection_detector"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "anomaly_detector"))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from auth import create_access_token, get_current_user, get_user_by_username, verify_or_dummy
from database import fetch_one
from models import LoginRequest

app = FastAPI(title="Secure AI Agent System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Login brute-force roak: 5 galat koshish => 10 minute ke liye us username par rok ----
MAX_FAILS, WINDOW_SEC = 5, 600
_failed = defaultdict(list)


def _recent_fails(username: str):
    now = time.time()
    _failed[username] = [t for t in _failed[username] if now - t < WINDOW_SEC]
    return _failed[username]


@app.get("/")
def root():
    return {"message": "Backend is running!"}


@app.get("/test-db")
def test_db():
    try:
        row = fetch_one("SELECT COUNT(*) AS n FROM students")
        return {"status": "connected", "students": row["n"]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# NOTE: public /signup hata diya gaya hai. Accounts sirf admin ya seed script banati hai.

@app.post("/login")
def login(data: LoginRequest):
    username = data.username.strip()
    if len(_recent_fails(username)) >= MAX_FAILS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    user = get_user_by_username(username)
    ok = verify_or_dummy(data.password, user["password_hash"] if user else None)
    if not ok:
        _failed[username].append(time.time())
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")

    _failed.pop(username, None)
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
    }


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")
    return user
