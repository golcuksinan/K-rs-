from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# pool_pre_ping: havuzdaki bağlantı DB tarafında koparsa (idle timeout, restart) SQLAlchemy
# onu sessizce yeniler. Kapalıyken kopan bağlantıyı alan ilk istek 500 yer.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()