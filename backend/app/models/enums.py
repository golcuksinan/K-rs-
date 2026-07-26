import enum

class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"
    mezun = "mezun"


class Sinif(int, enum.Enum):
    """Hesaplanan sınıf — DB'de saklanmaz, User.enrollment_year'dan anlık hesaplanır
    (bkz. app/core/academic.py). Sıralı int değerler bilinçli: CourseProfessor'daki
    target_grade_min/max ile aralık (BETWEEN) karşılaştırması yapılabilsin diye."""
    HAZIRLIK = 0
    BIR = 1
    IKI = 2
    UC = 3
    DORT = 4
    BES = 5
    ALTI = 6