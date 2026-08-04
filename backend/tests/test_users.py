"""Router: app/api/users.py (prefix /users)"""
from sqlalchemy import func

from app.core.academic import compute_sinif


class TestGetCurrentUser:
    def test_requires_auth(self, client):
        resp = client.get("/users/me")
        assert resp.status_code == 401

    def test_returns_expected_fields(self, client, student_headers, student, valid_department, valid_faculty, valid_university):
        resp = client.get("/users/me", headers=student_headers)
        assert resp.status_code == 200
        body = resp.json()

        assert body["role"] == "student"
        assert body["enrollment_year"] == student["user"].enrollment_year
        assert body["is_verified"] is True
        assert body["department_id"] == valid_department.id
        assert body["department_name"] == valid_department.name
        assert body["faculty_id"] == valid_faculty.id
        assert body["faculty_name"] == valid_faculty.name
        assert body["university_id"] == valid_university.id
        assert body["university_name"] == valid_university.name
        assert body["university_short_name"] == valid_university.short_name
        assert "id" not in body
        assert "email" not in body

    def test_current_grade_matches_compute_sinif(self, client, student_factory):
        entry = student_factory(enrollment_year=2023)
        login_resp = client.post("/auth/login", json={"email": entry["email"], "password": entry["password"]})
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 200
        expected = compute_sinif(2023)
        assert resp.json()["current_grade"] == expected.value

    def test_deleted_department_name_is_masked(self, client, student_headers, db_session, valid_department):
        valid_department.deleted_at = func.now()
        db_session.flush()

        body = client.get("/users/me", headers=student_headers).json()
        assert body["department_name"] == "Silinmiş Bölüm"
        assert body["department_id"] == valid_department.id

    def test_deleted_faculty_name_is_masked(self, client, student_headers, db_session, valid_faculty):
        valid_faculty.deleted_at = func.now()
        db_session.flush()

        body = client.get("/users/me", headers=student_headers).json()
        assert body["faculty_name"] == "Silinmiş Fakülte"

    def test_deleted_university_name_and_short_name_are_masked(self, client, student_headers, db_session, valid_university):
        valid_university.deleted_at = func.now()
        db_session.flush()

        body = client.get("/users/me", headers=student_headers).json()
        assert body["university_name"] == "Silinmiş Üniversite"
        assert body["university_short_name"] is None

    def test_admin_can_read_own_profile_too(self, client, admin_headers, admin):
        resp = client.get("/users/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_unverified_user_rejected(self, client, db_session, valid_department):
        # Bugün normal akışta doğrulanmamış kullanıcı oluşmuyor; guard'ın testi için
        # doğrudan DB'ye yazılır (bkz. deps.get_current_user).
        from datetime import date

        from app.core.security import create_access_token, hash_email, hash_password
        from app.models.user import User

        user = User(
            email_hash=hash_email("dogrulanmamis@posta.pau.edu.tr"),
            hashed_password=hash_password("sifre123"),
            is_verified=False,
            department_id=valid_department.id,
            enrollment_year=date.today().year,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 403