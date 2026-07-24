from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.security import is_valid_edu_tr_email

def _validate_password_complexity(v: str) -> str:
    if not any(char.isdigit() for char in v):
        raise ValueError("Şifre en az bir rakam içermelidir")
    return v

# ---------- Register ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def must_be_edu_tr(cls, v: str) -> str:
        if not is_valid_edu_tr_email(v):
            raise ValueError(".edu.tr uzantılı bir e-posta kullanmalısınız")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password_complexity(v)
    
class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


# ---------- Login ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Şifremi unuttum ----------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return _validate_password_complexity(v)
    
# ---------- Genel ----------

class MessageResponse(BaseModel):
    message: str