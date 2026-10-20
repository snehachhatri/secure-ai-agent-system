from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RequestPayload(BaseModel):
    request_text: str = Field(min_length=1, max_length=2000)