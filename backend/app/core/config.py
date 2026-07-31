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
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    # Havuz tükendiğinde istek 30 sn (SQLAlchemy varsayılanı) asılı kalmasın; sayaç gibi
    # hatası yutulan yollarda bu bekleme doğrudan kullanıcı isteğine yansıyordu.
    DB_POOL_TIMEOUT: int = 5
    # Virgülle ayrılmış origin listesi. Varsayılan "*" = dev davranışı korunur;
    # prod'da .env'den daraltılır. list[str] olarak tanımlanmadı: pydantic-settings
    # complex tipte env değerini JSON parse etmeye çalışır, "a,b" verilince patlar.
    ALLOWED_ORIGINS: str = "*"

    # Reverse proxy'lerin IP'leri, virgülle ayrılır. Boş = X-Forwarded-For'a güvenilmez.
    # ALLOWED_ORIGINS ile aynı gerekçeyle list[str] değil.
    TRUSTED_PROXY_IPS: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_proxy_ips_list(self) -> list[str]:
        return [ip.strip() for ip in self.TRUSTED_PROXY_IPS.split(",") if ip.strip()]

    class Config:
        env_file = ".env"

settings = Settings()