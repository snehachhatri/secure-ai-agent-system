from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

app = FastAPI()

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary demo credentials
DEMO_USERNAME = "customer1"
DEMO_PASSWORD = "customer123"

# JWT secret - demo ke liye
SECRET_KEY = "secure-ai-agent-secret-key"


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
def home():
    return {
        "message": "Secure AI Agent Backend is running"
    }


@app.post("/login")
def login(request: LoginRequest):

    # Check username and password
    if (
        request.username != DEMO_USERNAME
        or request.password != DEMO_PASSWORD
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT token
    token = jwt.encode(
        {
            "username": request.username,
            "exp": datetime.utcnow() + timedelta(hours=1)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }