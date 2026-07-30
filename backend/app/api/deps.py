from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _issued_before_password_change(user: User, issued_at: float | None) -> bool:
    """Şifre sıfırlandıysa o andan önce üretilmiş token kabul edilmez. iat taşımayan
    (sıfırlamadan eski) token'lar da elenir — tarafta kalınır."""
    if user.password_changed_at is None:
        return False
    return issued_at is None or issued_at < user.password_changed_at.timestamp()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmanız gerekiyor",
        )

    user_id, issued_at = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
        )

    if _issued_before_password_change(user, issued_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
        )

    # Bugün doğrulanmamış kullanıcı yaratılmıyor (verify-otp is_verified=True yazar);
    # guard ileride farklı bir yaratma yolu eklenirse yazma uçlarının açık kalmaması için.
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E-posta doğrulaması tamamlanmamış",
        )

    return user

def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekiyor",
        )
    return current_user

def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    user_id, issued_at = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    if not user.is_verified or _issued_before_password_change(user, issued_at):
        return None
    return user