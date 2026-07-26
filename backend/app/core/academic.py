"""Öğrencinin güncel sınıfını enrollment_year'dan state tutmadan hesaplayan yardımcılar.
Akademik yıl geçişi Eylül baz alınır (Eylül'den önce hâlâ bir önceki akademik yıldayız).
"""
from datetime import date

from app.models.enums import Sinif

ACADEMIC_YEAR_START_MONTH = 9  # Eylül


def get_current_academic_year(today: date | None = None) -> int:
    """İçinde bulunulan akademik yılın başlangıç yılını döner.
    Örn. Ekim 2026 -> 2026, Mart 2026 (Eylül henüz gelmedi) -> 2025."""
    today = today or date.today()
    if today.month >= ACADEMIC_YEAR_START_MONTH:
        return today.year
    return today.year - 1


def compute_sinif(enrollment_year: int, today: date | None = None) -> Sinif:
    """enrollment_year'a göre güncel sınıfı hesaplar. Program süresinden bağımsızdır;
    enum'un üst sınırını (6) aşan ya da negatif çıkan değerler [0, 6] aralığına clamp edilir."""
    current_academic_year = get_current_academic_year(today)
    yil_farki = current_academic_year - enrollment_year  # Hazırlık = 0

    clamped = max(0, min(yil_farki, Sinif.ALTI.value))
    return Sinif(clamped)