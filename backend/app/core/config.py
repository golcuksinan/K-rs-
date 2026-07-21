from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_PEPPER_KEY: str  # JWT SECRET_KEY'den tamamen farklı olmalı, asla rotate edilmemeli
    OTP_EXPIRE_MINUTES: int = 10
    class Config:
        env_file = ".env"

settings = Settings()