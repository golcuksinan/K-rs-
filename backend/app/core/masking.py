"""Silinmiş (soft-delete) üst kayıtların adlarının sızmasını engelleyen maskeleme.

Sadece **isim** maskelenir; id / kod gibi alanlar gerçek değerle döner.
İsim olmayan alanlar (University.short_name) maskelenmez, silinmişse None döner.
"""

from typing import Optional

DELETED_UNIVERSITY = "Silinmiş Üniversite"
DELETED_FACULTY = "Silinmiş Fakülte"
DELETED_DEPARTMENT = "Silinmiş Bölüm"
DELETED_COURSE = "Silinmiş Ders"


def masked_name(deleted_at, name: str, placeholder: str) -> str:
    return placeholder if deleted_at is not None else name


def masked_optional(deleted_at, value: Optional[str]) -> Optional[str]:
    """İsim olmayan alanlar için: silinmişse placeholder değil None."""
    return None if deleted_at is not None else value
