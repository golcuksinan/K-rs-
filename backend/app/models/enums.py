import enum

class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"