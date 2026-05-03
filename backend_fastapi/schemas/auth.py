"""Pydantic schemas for authentication (login / registro)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=80, description="Nome de usuário")
    password: str = Field(..., min_length=1, max_length=72)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        # Bcrypt tem limite de 72 bytes
        if len(v.encode('utf-8')) > 72:
            raise ValueError(
                f"A senha excede o limite de 72 bytes (enviado: {len(v.encode('utf-8'))} bytes)."
            )
        return v


class RegisterRequest(BaseModel):
    name: str = Field("", max_length=80)
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str = Field(..., min_length=8, max_length=72)
    university: Optional[str] = Field(None, max_length=50)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if " " in v:
            raise ValueError("O usuário não pode conter espaços.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter ao menos 8 caracteres.")
        if not re.search(r"[#@$%*]", v):
            raise ValueError('A senha deve incluir ao menos um caractere especial: # @ $ % *')
        # Bcrypt tem limite de 72 bytes. Verificar a codificação UTF-8.
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError(
                f"A senha excede o limite de 72 bytes (enviado: {len(password_bytes)} bytes). "
                "Reduza o número de caracteres especiais ou encurte a senha."
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("As senhas não coincidem.")
        return v


class AuthResponse(BaseModel):
    message: str = "OK"
    user_id: int
    username: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    is_admin: bool = False
    token: Optional[str] = None  # only if the client wants the token in body


class UserBrief(BaseModel):
    id: int
    username: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    is_verified: bool = False

    model_config = {"from_attributes": True}


class LogoutResponse(BaseModel):
    message: str = "Desconectado com sucesso."
