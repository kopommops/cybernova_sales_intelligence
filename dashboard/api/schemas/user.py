from pydantic import BaseModel, field_validator
from typing import Literal



class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be blank.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class ApproveUserRequest(BaseModel):
    role: Literal["salesperson", "sales_manager", "systems_manager"]


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    username:     str


class UserResponse(BaseModel):
    id:          int
    username:    str
    role:        str
    is_approved: bool


class MessageResponse(BaseModel):
    message: str

class DeleteUserRequest(BaseModel):
    password: str