from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_PEPPER_KEY: str  # JWT SECRET_KEY'den tamamen farklı olmalı, asla rotate edilmemeli
    OTP_EXPIRE_MINUTES: int = 10
    HF_API_TOKEN: str = ""
    HF_MODEL_URL: str = "https://router.huggingface.co/hf-inference/models/unitary/toxic-bert"
    # Virgülle ayrılmış origin listesi. Varsayılan "*" = dev davranışı korunur;
    # prod'da .env'den daraltılır. list[str] olarak tanımlanmadı: pydantic-settings
    # complex tipte env değerini JSON parse etmeye çalışır, "a,b" verilince patlar.
    ALLOWED_ORIGINS: str = "*"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"

settings = Settings()