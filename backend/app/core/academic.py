"""Öğrencinin güncel sınıfını enrollment_year'dan state tutmadan hesaplayan yardımcılar.
Akademik yıl geçişi Eylül baz alınır (Eylül'den önce hâlâ bir önceki akademik yıldayız).
"""
import re
from datetime import date

from app.models.enums import Sinif

ACADEMIC_YEAR_START_MONTH = 9  # Eylül

# Kayıt yılından sonra yorum yazılabilecek en son akademik yıl farkı. Uzatma, çift anadal ve
# yatay geçiş için geniş tutuldu; amaç makul olmayanı (2024 girişlinin 2015 dönemi) elemek.
MAX_STUDY_YEARS = 8

# E-posta yerel kısmındaki giriş yılını okuyan domain'e özgü desenler. PAÜ konvansiyonu:
# ad-soyad kısaltması + iki haneli yıl (asoyisim23 -> 2023); aynı adın ikinci sahibi için sona
# ayırt edici hane eklenir (isoyisim231 -> 2023), o yüzden harflerden sonraki İLK iki hane
# okunur, sondaki iki hane değil. Deseni olan domain'de kullanıcının beyanı yok sayılır —
# beyan kullanıcının elindedir, adres değildir. Deseni olmayan üniversitede beyan kullanılır;
# yeni üniversite eklenince buraya bir satır eklenir.
EMAIL_ENROLLMENT_YEAR_PATTERNS = {
    "posta.pau.edu.tr": re.compile(r"^\D*(\d{2})"),
}

# Hem "2023-2024 Güz" (katalog) hem "2025-Güz" (kısa) biçiminden baştaki yılı okur.
_TERM_START_YEAR = re.compile(r"^(\d{4})")


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


def is_plausible_enrollment_year(year: int, today: date | None = None) -> bool:
    """Gevşek sanity aralığı: 15 yıl geriye kadar, gelecek yıl yok."""
    current_year = (today or date.today()).year
    return current_year - 15 <= year <= current_year


def parse_enrollment_year_from_email(email: str, today: date | None = None) -> int | None:
    """E-postadan giriş yılını okur; domain'in deseni yoksa, desen tutmazsa veya çıkan yıl
    makul aralıkta değilse None döner (çağıran taraf kullanıcının beyanına düşer)."""
    normalized = email.strip().lower()
    local, _, domain = normalized.rpartition("@")
    pattern = EMAIL_ENROLLMENT_YEAR_PATTERNS.get(domain)
    if not pattern:
        return None

    match = pattern.search(local)
    if not match:
        return None

    year = 2000 + int(match.group(1))
    return year if is_plausible_enrollment_year(year, today) else None


def parse_term_start_year(term: str) -> int | None:
    """Dönem etiketinin başlangıç yılı; biçim tanınmazsa None (kontrol atlanır)."""
    match = _TERM_START_YEAR.match((term or "").strip())
    return int(match.group(1)) if match else None