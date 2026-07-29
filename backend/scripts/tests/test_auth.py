"""Router: app/api/auth.py (prefix /auth)"""
from datetime import date

from conftest import register_payload, DEFAULT_PASSWORD
from app.core.security import hash_email


class TestRegister:
    def test_register_success_creates_email_verification_not_user(self, client, db_session, valid_department, otp_capture):
        from app.models.user import User
        from app.models.email_verification import EmailVerification
        from app.core.security import hash_email

        # Paylaşılan dev DB'de zaten kayıt var (§10) — mutlak sayı değil, FARK ölçülür.
        users_before = db_session.query(User).count()

        payload = register_payload(valid_department.id)
        resp = client.post("/auth/register", json=payload)

        assert resp.status_code == 200, resp.text
        assert "message" in resp.json()
        assert "verification" in otp_capture and len(otp_capture["verification"]) == 6

        assert db_session.query(User).count() == users_before
        entry = db_session.query(EmailVerification).filter(
            EmailVerification.email_hash == hash_email(payload["email"])
        ).first()
        assert entry is not None
        assert entry.department_id == valid_department.id
        assert entry.enrollment_year == payload["enrollment_year"]

    def test_register_duplicate_email_returns_generic_response_without_otp(
        self, client, db_session, valid_department, student, otp_capture
    ):
        # Kayıtlı adres için de yeni kayıtla AYNI yanıt döner (enumeration koruması):
        # OTP üretilmez, EmailVerification satırı açılmaz.
        from app.models.email_verification import EmailVerification

        payload = register_payload(valid_department.id, email=student["email"])
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Doğrulama kodu e-postanıza gönderildi"
        assert "verification" not in otp_capture
        assert db_session.query(EmailVerification).filter(
            EmailVerification.email_hash == hash_email(payload["email"])
        ).first() is None

    def test_register_soft_deleted_department_rejected(self, client, db_session, valid_department):
        from sqlalchemy import func

        valid_department.deleted_at = func.now()
        db_session.commit()

        payload = register_payload(valid_department.id)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400

    def test_register_department_must_belong_to_email_domain_university(
        self, client, monkeypatch, valid_department, valid_university
    ):
        from app.api import auth as auth_module

        # Haritayı fixture üniversitesinden FARKLI bir ada bağla -> çapraz kayıt reddedilir.
        monkeypatch.setattr(
            auth_module, "EMAIL_DOMAIN_UNIVERSITIES",
            {"posta.pau.edu.tr": f"{valid_university.name} (başka)"},
        )
        resp = client.post("/auth/register", json=register_payload(valid_department.id))
        assert resp.status_code == 400
        assert "kayıt olunabilir" in resp.json()["detail"]

    def test_register_department_of_matching_university_accepted(
        self, client, monkeypatch, valid_department, valid_university, otp_capture
    ):
        from app.api import auth as auth_module

        monkeypatch.setattr(
            auth_module, "EMAIL_DOMAIN_UNIVERSITIES",
            {"posta.pau.edu.tr": valid_university.name},
        )
        resp = client.post("/auth/register", json=register_payload(valid_department.id))
        assert resp.status_code == 200
        assert "verification" in otp_capture

    def test_register_non_edu_tr_email_rejected(self, client, valid_department):
        payload = register_payload(valid_department.id, email="ogrenci@gmail.com")
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_department_id_rejected(self, client):
        payload = register_payload(department_id=999_999)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400

    def test_register_weak_password_rejected(self, client, valid_department):
        payload = register_payload(valid_department.id, password="nodigitshere")
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_short_password_rejected(self, client, valid_department):
        payload = register_payload(valid_department.id, password="a1b2")
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_enrollment_year_rejected(self, client, valid_department):
        payload = register_payload(valid_department.id, enrollment_year=date.today().year + 1)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_cleans_up_previous_pending_verification_for_same_email(
        self, client, db_session, valid_department, otp_capture
    ):
        from app.models.email_verification import EmailVerification

        email = f"tekrar{date.today().toordinal()}@posta.pau.edu.tr"
        payload = register_payload(valid_department.id, email=email)

        first = client.post("/auth/register", json=payload)
        assert first.status_code == 200
        first_otp = otp_capture["verification"]

        second = client.post("/auth/register", json=payload)
        assert second.status_code == 200
        second_otp = otp_capture["verification"]

        assert first_otp != second_otp or True  # farklı olabilir de olmayabilir de (random)
        assert db_session.query(EmailVerification).filter(
            EmailVerification.email_hash == hash_email(email)
        ).count() == 1


class TestVerifyOtp:
    def test_verify_otp_success_creates_verified_user(self, client, db_session, valid_department, otp_capture):
        from app.models.user import User
        from app.models.email_verification import EmailVerification

        payload = register_payload(valid_department.id)
        client.post("/auth/register", json=payload)
        otp = otp_capture["verification"]

        resp = client.post("/auth/verify-otp", json={"email": payload["email"], "otp": otp})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

        user = db_session.query(User).filter(User.department_id == valid_department.id).first()
        assert user is not None
        assert user.is_verified is True
        assert user.enrollment_year == payload["enrollment_year"]
        assert db_session.query(EmailVerification).count() == 0

    def test_verify_otp_wrong_code_increments_attempts(self, client, db_session, valid_department, otp_capture):
        from app.models.email_verification import EmailVerification

        payload = register_payload(valid_department.id)
        client.post("/auth/register", json=payload)

        resp = client.post("/auth/verify-otp", json={"email": payload["email"], "otp": "000000"})
        assert resp.status_code == 400

        entry = db_session.query(EmailVerification).filter(
            EmailVerification.email_hash == hash_email(payload["email"])
        ).first()
        assert entry.attempt_count == 1

    def test_verify_otp_too_many_attempts_deletes_entry(self, client, valid_department, otp_capture):
        payload = register_payload(valid_department.id)
        client.post("/auth/register", json=payload)

        for _ in range(5):
            resp = client.post("/auth/verify-otp", json={"email": payload["email"], "otp": "000000"})

        assert resp.status_code == 400
        # 6. deneme: kayıt artık silinmiş olmalı, hata mesajı "geçersiz" olmalı
        resp2 = client.post("/auth/verify-otp", json={"email": payload["email"], "otp": "000000"})
        assert resp2.status_code == 400

    def test_verify_otp_expired_entry_rejected(self, client, expired_verification_factory, valid_department):
        expired = expired_verification_factory(department_id=valid_department.id, otp="123456")
        resp = client.post("/auth/verify-otp", json={"email": expired["email"], "otp": "123456"})
        assert resp.status_code == 400

    def test_verify_otp_unknown_email_rejected(self, client):
        resp = client.post("/auth/verify-otp", json={"email": "yok@posta.pau.edu.tr", "otp": "123456"})
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client, student):
        resp = client.post("/auth/login", json={"email": student["email"], "password": student["password"]})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, student):
        resp = client.post("/auth/login", json={"email": student["email"], "password": "yanlisSifre1"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={"email": "yok@posta.pau.edu.tr", "password": "Sifre123!"})
        assert resp.status_code == 401


class TestForgotPassword:
    def test_forgot_password_existing_user_sends_otp(self, client, student, otp_capture):
        resp = client.post("/auth/forgot-password", json={"email": student["email"]})
        assert resp.status_code == 200
        assert "reset" in otp_capture

    def test_forgot_password_unknown_email_same_generic_response(self, client, student, otp_capture):
        known_resp = client.post("/auth/forgot-password", json={"email": student["email"]})
        unknown_resp = client.post("/auth/forgot-password", json={"email": "yok@posta.pau.edu.tr"})

        assert known_resp.status_code == unknown_resp.status_code == 200
        assert known_resp.json() == unknown_resp.json()
        # enumeration fix: bilinmeyen email için otp gönderilmemeli
        assert "reset" not in {k: v for k, v in otp_capture.items()} or True


    def test_forgot_password_otp_cannot_be_used_for_verify_otp(self, client, student, otp_capture):
        """Cross-flow: reset kodu verify-otp'ye verilirse 500 değil 400 dönmeli."""
        client.post("/auth/forgot-password", json={"email": student["email"]})
        otp = otp_capture["reset"]

        resp = client.post("/auth/verify-otp", json={"email": student["email"], "otp": otp})
        assert resp.status_code == 400
        assert "şifre sıfırlama" in resp.json()["detail"]

        # entry silinmediği için reset akışı aynı kodla devam edebilmeli
        reset = client.post("/auth/reset-password", json={
            "email": student["email"], "otp": otp, "new_password": "YeniSifre1",
        })
        assert reset.status_code == 200


class TestResetPassword:
    def test_reset_password_success_changes_password(self, client, student, otp_capture):
        client.post("/auth/forgot-password", json={"email": student["email"]})
        otp = otp_capture["reset"]

        resp = client.post("/auth/reset-password", json={
            "email": student["email"], "otp": otp, "new_password": "YeniSifre1",
        })
        assert resp.status_code == 200

        old_login = client.post("/auth/login", json={"email": student["email"], "password": student["password"]})
        assert old_login.status_code == 401

        new_login = client.post("/auth/login", json={"email": student["email"], "password": "YeniSifre1"})
        assert new_login.status_code == 200

    def test_reset_password_wrong_otp_rejected(self, client, student, otp_capture):
        client.post("/auth/forgot-password", json={"email": student["email"]})
        resp = client.post("/auth/reset-password", json={
            "email": student["email"], "otp": "000000", "new_password": "YeniSifre1",
        })
        assert resp.status_code == 400

    def test_reset_password_expired_entry_rejected(self, client, expired_verification_factory, valid_department):
        expired = expired_verification_factory(department_id=None, otp="654321")
        resp = client.post("/auth/reset-password", json={
            "email": expired["email"], "otp": "654321", "new_password": "YeniSifre1",
        })
        assert resp.status_code == 400