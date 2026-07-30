import enum

class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"
    mezun = "mezun"


class Sinif(int, enum.Enum):
    """Hesaplanan sınıf — DB'de saklanmaz, User.enrollment_year'dan anlık hesaplanır
    (bkz. app/core/academic.py). Yalnızca GET /users/me'de dönüyor: ders listelerini
    sınıfa göre süzmek bilinçli olarak reddedildi (alttan/üstten ders — §9.3)."""
    HAZIRLIK = 0
    BIR = 1
    IKI = 2
    UC = 3
    DORT = 4
    BES = 5
    ALTI = 6