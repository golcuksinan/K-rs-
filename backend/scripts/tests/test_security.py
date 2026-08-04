"""Güvenlik odaklı uçtan uca testler (CLAUDE.md §9.2 "Kapsamlı pentest").

Statik `/security-review` taramasından ayrı ve ona ek: saldırı senaryoları gerçek HTTP
istekleriyle, mevcut `client` fixture'ı üzerinden denenir.

Kapsam dışında bırakılanlar (başka dosyada, tekrarlanmıyor):
- rate limit 429 doğrulaması → test_rate_limiting.py
- register/forgot-password enumeration → test_auth.py (burada yalnızca login'inki var)
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.models.review import Review
from app.models.user import User
from conftest import AI_TEST_APPROVE, DEFAULT_PASSWORD, register_payload


def _token(user_id, *, secret=None, lifetime=timedelta(minutes=30), **extra_claims):
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + lifetime}
    payload.update(extra_claims)
    return jwt.encode(payload, secret or settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _review_payload(course_professor_id, **overrides):
    payload = {
        "course_professor_id": course_professor_id,
        "teaching_score": 4,
        "difficulty_score": 3,
        "fairness_score": 5,
        "comment": "normal bir yorum",
    }
    payload.update(overrides)
    return payload


# Var olmayan id'ler bilinçli: yetki kontrolü dependency'de, handler gövdesinden önce
# çalışıyor — kayıt kurmadan 401/403 ölçülebiliyor. Bir uç 404 dönerse yetki kontrolü
# handler'ın içine kaymış demektir, test bunu yakalar.
ADMIN_ENDPOINTS = [
    ("post", "/universities", {"name": "X", "city": "Y"}),
    ("patch", "/universities/999999", {"name": "X"}),
    ("delete", "/universities/999999", None),
    ("post", "/faculties", {"university_id": 999999, "name": "X"}),
    ("patch", "/faculties/999999", {"name": "X"}),
    ("delete", "/faculties/999999", None),
    ("post", "/departments", {"faculty_id": 999999, "name": "X"}),
    ("patch", "/departments/999999", {"name": "X"}),
    ("delete", "/departments/999999", None),
    ("post", "/courses", {"department_id": 999999, "name": "X", "code": "X"}),
    ("patch", "/courses/999999", {"name": "X"}),
    ("delete", "/courses/999999", None),
    ("post", "/course-professors", {"course_id": 999999, "professor_id": 999999, "term": "2025-Güz"}),
    ("get", "/reviews/pending", None),
    ("patch", "/reviews/999999/status", {"status": "approved"}),
    ("patch", "/reviews/999999/edit-status", {"status": "approved"}),
    ("get", "/reports/pending", None),
    ("patch", "/reports/999999/status", {"status": "resolved"}),
    ("get", "/admin/stats", None),
    ("get", "/admin/stats/events", None),
]

AUTH_ENDPOINTS = [
    ("get", "/users/me", None),
    ("get", "/reviews/me", None),
    ("get", "/reports/me", None),
    ("post", "/reviews", {"course_professor_id": 1, "teaching_score": 3,
                          "difficulty_score": 3, "fairness_score": 3}),
    ("post", "/reports", {"review_id": 1, "reason": "sebep"}),
    ("patch", "/reviews/999999", {"teaching_score": 3, "difficulty_score": 3, "fairness_score": 3}),
    ("delete", "/reviews/999999", None),
]


def _call(client, method, path, body, headers=None):
    kwargs = {"headers": headers} if headers else {}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


class TestYetkiMatrisi:
    @pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS)
    def test_admin_endpoint_rejects_student_token(self, client, student_headers, method, path, body):
        resp = _call(client, method, path, body, student_headers)
        assert resp.status_code == 403, f"{method.upper()} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS)
    def test_admin_endpoint_rejects_anonymous(self, client, method, path, body):
        resp = _call(client, method, path, body)
        assert resp.status_code == 401, f"{method.upper()} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("method,path,body", AUTH_ENDPOINTS)
    def test_auth_endpoint_rejects_anonymous(self, client, method, path, body):
        resp = _call(client, method, path, body)
        assert resp.status_code == 401, f"{method.upper()} {path} -> {resp.status_code}"

    def test_unverified_user_is_rejected(self, client, db_session, student):
        student["user"].is_verified = False
        db_session.commit()

        resp = client.get("/users/me", headers=_auth(_token(student["user"].id)))
        assert resp.status_code == 403


class TestIDOR:
    def test_cannot_edit_another_users_review(
        self, client, student_headers, second_student_headers, course_professor, fake_ai_service
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "ele geçirildi"},
            headers=second_student_headers,
        )
        assert resp.status_code == 403

    def test_cannot_delete_another_users_review(
        self, client, db_session, student_headers, second_student_headers, course_professor, fake_ai_service
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.delete(f"/reviews/{review_id}", headers=second_student_headers)
        assert resp.status_code == 403
        assert db_session.query(Review).filter(Review.id == review_id).first() is not None

    def test_reviews_me_only_returns_own_reviews(
        self, client, student, second_student, student_headers, second_student_headers, course_professor,
        fake_ai_service,
    ):
        client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)

        resp = client.get("/reviews/me", headers=second_student_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestJWTKurcalama:
    def test_malformed_token_rejected(self, client):
        resp = client.get("/users/me", headers=_auth("bu.bir.token.degil"))
        assert resp.status_code == 401

    def test_expired_token_rejected(self, client, student):
        token = _token(student["user"].id, lifetime=timedelta(minutes=-5))
        assert client.get("/users/me", headers=_auth(token)).status_code == 401

    def test_token_signed_with_wrong_secret_rejected(self, client, student):
        token = _token(student["user"].id, secret=settings.SECRET_KEY + "-sahte")
        assert client.get("/users/me", headers=_auth(token)).status_code == 401

    def test_token_for_nonexistent_user_rejected(self, client):
        assert client.get("/users/me", headers=_auth(_token(999999))).status_code == 401

    def test_raw_token_without_bearer_scheme_rejected(self, client, student):
        token = _token(student["user"].id)
        assert client.get("/users/me", headers={"Authorization": token}).status_code == 401

    def test_role_claim_in_token_does_not_grant_admin(self, client, student):
        """Rol token'dan değil DB'den okunuyor: geçerli imzalı bir token'a role=admin
        eklemek yetki vermez. `create_access_token` bugün rolü zaten yazmıyor; bu test
        ileride payload'a rol eklenip yetkinin oradan okunmasını engellemek için var."""
        token = _token(student["user"].id, role="admin", is_admin=True)

        assert client.get("/users/me", headers=_auth(token)).status_code == 200
        assert client.get("/reviews/pending", headers=_auth(token)).status_code == 403


class TestMassAssignment:
    def test_review_create_ignores_status_and_owner_fields(
        self, client, db_session, student, second_student, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews",
            json=_review_payload(
                course_professor.id,
                status="approved",
                user_id=second_student["user"].id,
                has_pending_edit=True,
            ),
            headers=student_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

        review = db_session.query(Review).filter(Review.id == resp.json()["id"]).first()
        assert review.user_id == student["user"].id
        assert review.status == "pending"
        assert review.has_pending_edit is False

    def test_review_update_ignores_status_field(
        self, client, db_session, student_headers, course_professor, fake_ai_service
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        # comment boş bırakılamaz: `analyze_review_with_hf` boş metni moderasyona sokmadan
        # APPROVED döner, o zaman testin ölçtüğü şey mass assignment olmaktan çıkar.
        resp = client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 2, "difficulty_score": 2, "fairness_score": 2,
                  "comment": "guncellenmis yorum", "status": "approved"},
            headers=student_headers,
        )
        assert resp.status_code == 200

        db_session.expire_all()
        assert db_session.query(Review).filter(Review.id == review_id).first().status == "pending"

    def test_register_cannot_self_assign_admin_role(
        self, client, db_session, valid_department, otp_capture
    ):
        payload = register_payload(valid_department.id, role="admin", is_verified=True)
        assert client.post("/auth/register", json=payload).status_code == 200

        verify = client.post(
            "/auth/verify-otp",
            json={"email": payload["email"], "otp": otp_capture["verification"]},
        )
        assert verify.status_code == 200

        headers = _auth(verify.json()["access_token"])
        assert client.get("/reviews/pending", headers=headers).status_code == 403


class TestSQLInjection:
    PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        '" OR 1=1 --',
        "a%' --",
        "\\'",
        "1; SELECT pg_sleep(5)--",
        "%%",
        "__",
    ]

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_search_endpoints_survive_injection_payloads(self, client, valid_university, payload):
        endpoints = [
            f"/universities?search={payload}",
            f"/faculties?university_id={valid_university.id}&search={payload}",
            f"/departments?search={payload}",
            f"/courses?search={payload}",
            f"/professors?search={payload}",
        ]
        for url in endpoints:
            resp = client.get(url)
            assert resp.status_code == 200, f"{url} -> {resp.status_code} {resp.text[:200]}"
            assert isinstance(resp.json()["items"], list)

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_users_table_intact_after_injection_attempts(self, client, db_session, payload):
        before = db_session.query(User).count()
        client.get(f"/courses?search={payload}")
        client.get(f"/professors?search={payload}")
        assert db_session.query(User).count() == before


class TestAnonimlik:
    LEAKY_KEYS = {"user_id", "email", "email_hash", "hashed_password", "reporter_id"}

    def _assert_clean(self, obj):
        leaked = self.LEAKY_KEYS & set(obj)
        assert not leaked, f"sızan alan: {leaked}"

    def test_public_review_list_hides_author(
        self, client, student_headers, course_professor, fake_ai_service
    ):
        client.post(
            "/reviews",
            json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE),
            headers=student_headers,
        )

        resp = client.get(f"/reviews?course_professor_id={course_professor.id}")
        items = resp.json()["items"]
        assert items, "approved review listede görünmeli"
        for item in items:
            self._assert_clean(item)

    def test_course_professor_detail_hides_authors(
        self, client, student_headers, course_professor, fake_ai_service
    ):
        client.post(
            "/reviews",
            json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE),
            headers=student_headers,
        )

        resp = client.get(f"/course-professors/{course_professor.id}")
        assert resp.status_code == 200
        self._assert_clean(resp.json())

    def test_professor_detail_hides_authors(
        self, client, student_headers, course_professor, valid_professor, fake_ai_service
    ):
        client.post(
            "/reviews",
            json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE),
            headers=student_headers,
        )

        resp = client.get(f"/professors/{valid_professor.id}")
        assert resp.status_code == 200
        for course in resp.json()["courses"]:
            self._assert_clean(course)

    def test_users_me_hides_identity(self, client, student_headers):
        body = client.get("/users/me", headers=student_headers).json()
        self._assert_clean(body)
        assert "id" not in body

    def test_admin_view_of_pending_reviews_hides_author(
        self, client, student_headers, admin_headers, course_professor, fake_ai_service
    ):
        client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)

        resp = client.get(f"/reviews/pending?course_professor_id={course_professor.id}", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        for item in items:
            self._assert_clean(item)


class TestLoginEnumeration:
    def test_unknown_user_and_wrong_password_are_indistinguishable(self, client, student):
        unknown = client.post(
            "/auth/login",
            json={"email": "hicyok@posta.pau.edu.tr", "password": DEFAULT_PASSWORD},
        )
        wrong_password = client.post(
            "/auth/login",
            json={"email": student["email"], "password": "YanlisSifre1"},
        )

        assert unknown.status_code == wrong_password.status_code == 401
        assert unknown.json() == wrong_password.json()
