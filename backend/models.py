from pydantic import BaseModel

class SignupRequest(BaseModel):
    username: str
    password: str
    role: str = "user"   # "user" ya "admin"

class LoginRequest(BaseModel):
    username: str
    password: str

class RequestPayload(BaseModel):
    request_text: str