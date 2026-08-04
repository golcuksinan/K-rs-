from pydantic import field_validator
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
    # Sync uçlar anyio threadpool'unda koşar; her handler tepede 2 DB bağlantısı tutabildiği
    # için tavan havuza göre daraltılır: 2 × token ≤ DB_POOL_SIZE + DB_MAX_OVERFLOW.
    # Varsayılan anyio'nunkiyle aynı, yerel davranış değişmez.
    THREADPOOL_TOKENS: int = 40
    # Virgülle ayrılmış origin listesi. Varsayılan "*" = dev davranışı korunur;
    # prod'da .env'den daraltılır. list[str] olarak tanımlanmadı: pydantic-settings
    # complex tipte env değerini JSON parse etmeye çalışır, "a,b" verilince patlar.
    ALLOWED_ORIGINS: str = "*"

    # Olay anında rebuild gerektirmeden kısılabilsin diye env'de; slowapi sözdizimi,
    # ";" ile birden çok pencere verilebilir.
    # Kovalar uç başına + IP başına. Kampüs NAT'ı tek IP olduğu için değerler tek kullanıcıya
    # değil kalabalığa göre seçildi; kapasiteyi limiter değil --limit-concurrency koruyor.
    RATE_LIMIT_DEFAULT: str = "20/second;600/minute"
    # §3.4'e (başarısızlık say, e-posta ekseninde) kadar geçici: 5/dakika NAT altında tüm
    # kampüsün giriş kotasıydı.
    RATE_LIMIT_AUTH: str = "20/minute"
    # Yalnızca başarısız giriş denemeleri, IP başına. Kalabalık başarılı giriş üretir,
    # spraying neredeyse tamamen başarısız — ikisi istek sayısında benzeşir, burada ayrışır.
    # RATE_LIMIT_AUTH'tan dar olmalı, yoksa istek sayacı önce dolar ve bu hiç tetiklenmez.
    RATE_LIMIT_AUTH_FAILURES: str = "10/minute"
    # Aynı sayacın e-posta ekseni: kendi adresiyle giren kullanıcı kimseyle kova paylaşmaz,
    # tek hesabı hedefleyen saldırgan IP değiştirse de buraya takılır. İki eksen birlikte
    # çalışır, biri diğerinin yerine geçmez.
    RATE_LIMIT_AUTH_FAILURES_EMAIL: str = "5/minute"

    # Cloudflare'in Transform Rule ile eklediği gizli değer. Boş = kilit kapalı (yerel/compose).
    CF_ORIGIN_SECRET: str = ""

    # Reverse proxy'lerin IP'leri, virgülle ayrılır. Boş = X-Forwarded-For'a güvenilmez.
    # ALLOWED_ORIGINS ile aynı gerekçeyle list[str] değil.
    TRUSTED_PROXY_IPS: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_scheme(cls, value: str) -> str:
        # Heroku DATABASE_URL'i postgres:// ile üretir ve parola rotate ettikçe yeniden yazar,
        # elle düzeltilemez; SQLAlchemy 2.x ise bu alias'ı tanımıyor.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_proxy_ips_list(self) -> list[str]:
        return [ip.strip() for ip in self.TRUSTED_PROXY_IPS.split(",") if ip.strip()]

    class Config:
        env_file = ".env"

settings = Settings()