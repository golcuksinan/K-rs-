from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from app.core.academic import is_plausible_enrollment_year, parse_enrollment_year_from_email
from app.core.security import is_valid_edu_tr_email

def _validate_password_complexity(v: str) -> str:
    if not any(char.isdigit() for char in v):
        raise ValueError("Şifre en az bir rakam içermelidir")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    department_id: int
    enrollment_year: Optional[int] = Field(
        default=None,
        description="Üniversiteye giriş yılı; e-postasında yıl taşıyan üniversitelerde yok sayılır",
    )

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

    @model_validator(mode="after")
    def resolve_enrollment_year(self):
        """E-posta yılı taşıyorsa beyan yok sayılır (beyan kullanıcının elinde, adres değil).
        Deseni olmayan üniversitede beyan zorunludur ve gevşek sanity aralığından geçer."""
        from_email = parse_enrollment_year_from_email(self.email)
        if from_email is not None:
            self.enrollment_year = from_email
            return self

        if self.enrollment_year is None:
            raise ValueError("Giriş yılı gereklidir")
        if not is_plausible_enrollment_year(self.enrollment_year):
            raise ValueError("Geçerli bir giriş yılı giriniz")
        return self


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


class MessageResponse(BaseModel):
    message: str