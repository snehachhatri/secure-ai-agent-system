import os
import sys
import time
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "policy_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "injection_detector"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "anomaly_detector"))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from audit import write_alert, write_log
from auth import create_access_token, get_current_user, get_user_by_username, verify_or_dummy
from database import fetch_one
from detector import detect
from models import LoginRequest, RequestPayload

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


# ---------------- Gateway (Step 1): injection check + audit log ----------------

@app.post("/request")
def handle_request(payload: RequestPayload, user: dict = Depends(get_current_user)):
    if user["is_locked"]:
        raise HTTPException(status_code=403, detail="Account locked. Contact the administrator.")

    text = payload.request_text

    # 1. Prompt injection check (agent se PEHLE)
    inj = detect(text)
    details = {"injection_score": inj.risk_score, "signals": inj.signals,
               "categories": sorted({m["category"] for m in inj.matches})}

    if inj.action == "block":
        try:
            write_log(user, text, "PROMPT_INJECTION", "blocked", inj.reason, "injection_detector", details)
            write_alert(user["user_id"], "PROMPT_INJECTION", "high", inj.reason)
        except Exception as e:      # block to ho hi raha hai; log fail hua to server par dikhao
            print("AUDIT WRITE FAILED (blocked request):", e)
        # User ko detail nahi (warna attacker seekh jayega ki kya pakda gaya)
        return {"decision": "blocked", "message": "Request blocked. This attempt has been logged."}

    # 2. Audit log likhe bina aage nahi badhte (fail closed)
    try:
        write_log(user, text, "NONE", "pending", "passed injection check", "injection_detector", details)
        if inj.action == "flag":
            write_alert(user["user_id"], "SUSPICIOUS_REQUEST", "medium", inj.reason)
    except Exception as e:
        print("AUDIT WRITE FAILED:", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # Agent, policy engine aur DB actions agle steps mein judenge
    return {"decision": "pending", "message": "Request passed the security check. The agent is not connected yet."}
