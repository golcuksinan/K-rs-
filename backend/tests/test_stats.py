"""Admin metrik uçları: `/admin/stats` (anlık durum) ve `/admin/stats/events` (olay sayaçları).

⚠️ Paylaşılan dev DB'de mutlak satır sayısı iddia edilemez — her test ölçümü öncesi/sonrası
FARK üzerinden yapar. Sayaçlar da aynı sebeple delta ölçer; testte artan sayaç rollback'le
geri gider (conftest `_isolate_metrics`).
"""
from uuid import uuid4

import pytest

from app.services import metrics
from conftest import AI_TEST_APPROVE, DEFAULT_PASSWORD, review_payload


def _stats(client, headers):
    resp = client.get("/admin/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _event_totals(client, headers, days=30):
    resp = client.get(f"/admin/stats/events?days={days}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["totals"]


class _SentinelEvent:
    """`Event` enum'una eklenmeden sayılabilen tek kullanımlık olay; `increment()` yalnızca
    `.value` okur."""

    def __init__(self):
        self.value = f"test.izolasyon_{uuid4().hex[:8]}"


def _counter_count(event_value):
    """Testin kendi (rollback edilen) transaction'ından değil, ayrı bir bağlantıdan okur —
    iddia edilen tam olarak sayacın commit edilmiş olması."""
    from app.db.session import SessionLocal
    from app.models.event_counter import EventDailyCounter

    session = SessionLocal()
    try:
        return session.query(EventDailyCounter.count).filter(
            EventDailyCounter.event == event_value
        ).scalar()
    finally:
        session.close()


class TestPlatformStats:
    def test_response_shape(self, client, admin_headers):
        data = _stats(client, admin_headers)

        assert set(data) == {"generated_at", "users", "content", "data_health", "moderation"}
        assert set(data["content"]) == {
            "universities", "faculties", "departments", "courses",
            "course_departments", "professors", "course_professors",
        }
        assert set(data["data_health"]) == {
            "courses_without_professor", "course_departments_without_curriculum",
        }
        assert set(data["users"]["by_role"]) == {"student", "admin", "mezun"}
        assert set(data["moderation"]) == {
            "reviews_total", "reviews_by_status", "reviews_with_pending_edit",
            "reports_total", "reports_by_status",
            "pending_registration_verifications", "pending_password_resets",
        }
        assert set(data["moderation"]["reviews_by_status"]) >= {"pending", "approved", "rejected"}
        assert set(data["moderation"]["reports_by_status"]) >= {"pending", "resolved", "dismissed"}

    def test_counts_are_non_negative_integers(self, client, admin_headers):
        data = _stats(client, admin_headers)

        for block in ("content", "data_health"):
            for name, value in data[block].items():
                assert isinstance(value, int) and value >= 0, f"{block}.{name} = {value}"
        assert data["users"]["total"] == data["users"]["verified"] + data["users"]["unverified"]

    def test_user_totals_match_role_breakdown(self, client, admin_headers):
        data = _stats(client, admin_headers)["users"]
        assert sum(data["by_role"].values()) == data["total"]
        assert sum(data["by_enrollment_year"].values()) == data["total"]

    def test_new_user_increases_total(self, client, admin_headers, student_factory):
        before = _stats(client, admin_headers)["users"]
        student_factory()
        after = _stats(client, admin_headers)["users"]

        assert after["total"] == before["total"] + 1
        assert after["by_role"]["student"] == before["by_role"]["student"] + 1

    def test_new_course_increases_content_counts(
        self, client, admin_headers, valid_department, make_course
    ):
        before = _stats(client, admin_headers)["content"]
        make_course(valid_department)
        after = _stats(client, admin_headers)["content"]

        assert after["courses"] == before["courses"] + 1
        assert after["course_departments"] == before["course_departments"] + 1

    def test_course_without_professor_is_counted_as_data_health(
        self, client, admin_headers, valid_department, make_course
    ):
        before = _stats(client, admin_headers)["data_health"]
        make_course(valid_department)
        after = _stats(client, admin_headers)["data_health"]

        assert after["courses_without_professor"] == before["courses_without_professor"] + 1

    def test_course_department_without_curriculum_is_counted(
        self, client, admin_headers, valid_department, make_course
    ):
        before = _stats(client, admin_headers)["data_health"]
        make_course(valid_department)
        after = _stats(client, admin_headers)["data_health"]

        assert (
            after["course_departments_without_curriculum"]
            == before["course_departments_without_curriculum"] + 1
        )

    def test_deleted_course_leaves_curriculum_gap_count(
        self, client, admin_headers, valid_department, make_course
    ):
        before = _stats(client, admin_headers)["data_health"]
        course = make_course(valid_department)

        deleted = client.delete(f"/courses/{course.id}", headers=admin_headers)
        assert deleted.status_code in (200, 204), deleted.text

        after = _stats(client, admin_headers)["data_health"]
        assert (
            after["course_departments_without_curriculum"]
            == before["course_departments_without_curriculum"]
        )

    def test_new_review_increases_pending_count(
        self, client, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        before = _stats(client, admin_headers)["moderation"]
        created = client.post(
            "/reviews", json=review_payload(course_professor.id, comment="normal yorum"),
            headers=student_headers,
        )
        assert created.status_code == 201, created.text
        after = _stats(client, admin_headers)["moderation"]

        assert after["reviews_total"] == before["reviews_total"] + 1
        assert after["reviews_by_status"]["pending"] == before["reviews_by_status"]["pending"] + 1

    def test_pending_edit_is_counted(
        self, client, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        created = client.post(
            "/reviews", json=review_payload(course_professor.id, AI_TEST_APPROVE), headers=student_headers
        )
        review_id = created.json()["id"]
        client.patch(
            f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers
        )

        before = _stats(client, admin_headers)["moderation"]
        client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1,
                  "comment": "düzeltildi"},
            headers=student_headers,
        )
        after = _stats(client, admin_headers)["moderation"]

        assert after["reviews_with_pending_edit"] == before["reviews_with_pending_edit"] + 1

    def test_new_report_is_counted(
        self, client, admin_headers, student_headers, second_student_headers,
        course_professor, fake_ai_service,
    ):
        created = client.post(
            "/reviews", json=review_payload(course_professor.id, AI_TEST_APPROVE), headers=student_headers
        )
        review_id = created.json()["id"]

        before = _stats(client, admin_headers)["moderation"]
        resp = client.post(
            "/reports", json={"review_id": review_id, "reason": "uygunsuz"},
            headers=second_student_headers,
        )
        assert resp.status_code == 201, resp.text
        after = _stats(client, admin_headers)["moderation"]

        assert after["reports_total"] == before["reports_total"] + 1
        assert after["reports_by_status"]["pending"] == before["reports_by_status"]["pending"] + 1


class TestEventStats:
    def test_window_is_zero_filled(self, client, admin_headers):
        resp = client.get("/admin/stats/events?days=7", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["days"] == 7
        assert len(data["series"]) == 7
        assert [row["day"] for row in data["series"]] == sorted(row["day"] for row in data["series"])
        assert data["series"][0]["day"] == data["start_day"]
        assert data["series"][-1]["day"] == data["end_day"]
        # Her gün, bilinen her olay için bir sayı taşır: istemci boşluk doldurmaz.
        for row in data["series"]:
            assert set(row["counts"]) == set(data["events"])
            assert all(value >= 0 for value in row["counts"].values())
        assert set(data["events"]) >= set(metrics.ALL_EVENTS)

    def test_totals_match_series(self, client, admin_headers, student):
        client.post("/auth/login", json={"email": student["email"], "password": DEFAULT_PASSWORD})
        data = client.get("/admin/stats/events?days=30", headers=admin_headers).json()

        for event, total in data["totals"].items():
            assert total == sum(row["counts"][event] for row in data["series"])

    @pytest.mark.parametrize("days", [0, 366, -1])
    def test_days_out_of_range_is_422(self, client, admin_headers, days):
        assert client.get(f"/admin/stats/events?days={days}", headers=admin_headers).status_code == 422

    def test_successful_login_is_counted(self, client, admin_headers, student):
        before = _event_totals(client, admin_headers)
        resp = client.post(
            "/auth/login", json={"email": student["email"], "password": DEFAULT_PASSWORD}
        )
        assert resp.status_code == 200
        after = _event_totals(client, admin_headers)

        assert after["auth.login_succeeded"] == before["auth.login_succeeded"] + 1
        assert after["auth.login_failed"] == before["auth.login_failed"]

    def test_failed_login_is_counted(self, client, admin_headers, student):
        before = _event_totals(client, admin_headers)
        resp = client.post("/auth/login", json={"email": student["email"], "password": "yanlisparola1"})
        assert resp.status_code == 401
        after = _event_totals(client, admin_headers)

        assert after["auth.login_failed"] == before["auth.login_failed"] + 1

    def test_login_of_unknown_user_is_counted(self, client, admin_headers):
        before = _event_totals(client, admin_headers)
        resp = client.post(
            "/auth/login",
            json={"email": "hicyok@posta.pau.edu.tr", "password": DEFAULT_PASSWORD},
        )
        assert resp.status_code == 401
        after = _event_totals(client, admin_headers)

        assert after["auth.login_failed"] == before["auth.login_failed"] + 1

    def test_register_and_mail_are_counted(self, client, admin_headers, valid_department, otp_capture):
        from conftest import register_payload

        before = _event_totals(client, admin_headers)
        resp = client.post("/auth/register", json=register_payload(valid_department.id))
        assert resp.status_code == 200, resp.text
        after = _event_totals(client, admin_headers)

        assert after["auth.register_started"] == before["auth.register_started"] + 1
        # ⚠️ Mail sayacı email_service.py'de: SMTP gerçek olunca ölçüm yerinde kalsın diye.
        # otp_capture auth.py'deki adı sahteler, gerçek fonksiyon çağrılmaz → sayaç artmaz.
        assert after["mail.verification_sent"] == before["mail.verification_sent"]

    def test_verification_mail_counter_lives_in_email_service(self, client, admin_headers):
        from app.services import email_service

        before = _event_totals(client, admin_headers)
        email_service.send_verification_email("ogrenci@posta.pau.edu.tr", "123456")
        after = _event_totals(client, admin_headers)

        assert after["mail.verification_sent"] == before["mail.verification_sent"] + 1

    def test_failed_send_is_not_counted_as_sent(self, client, admin_headers, monkeypatch):
        from app.services import email_service

        monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "test-key")

        def _boom(*args, **kwargs):
            raise RuntimeError("bağlantı yok")

        monkeypatch.setattr(email_service.resend.Emails, "send", _boom)

        before = _event_totals(client, admin_headers)
        email_service.send_verification_email("ogrenci@posta.pau.edu.tr", "123456")
        after = _event_totals(client, admin_headers)

        assert after["mail.verification_sent"] == before["mail.verification_sent"]
        assert after["mail.failed"] == before["mail.failed"] + 1

    def test_review_creation_is_counted(
        self, client, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        before = _event_totals(client, admin_headers)
        client.post("/reviews", json=review_payload(course_professor.id, AI_TEST_APPROVE), headers=student_headers)
        after = _event_totals(client, admin_headers)

        assert after["review.created"] == before["review.created"] + 1
        # Arka plan moderasyonu da kendi kararını sayar (fake_ai_service → approved).
        assert after["moderation.approved"] == before["moderation.approved"] + 1

    def test_admin_decision_is_counted(
        self, client, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        created = client.post(
            "/reviews", json=review_payload(course_professor.id, AI_TEST_APPROVE), headers=student_headers
        )
        review_id = created.json()["id"]

        before = _event_totals(client, admin_headers)
        client.patch(
            f"/reviews/{review_id}/status", json={"status": "rejected"}, headers=admin_headers
        )
        after = _event_totals(client, admin_headers)

        assert after["review.rejected"] == before["review.rejected"] + 1
        assert after["review.approved"] == before["review.approved"]

    def test_first_recorded_day_is_reported(self, client, admin_headers, student):
        client.post("/auth/login", json={"email": student["email"], "password": DEFAULT_PASSWORD})
        data = client.get("/admin/stats/events?days=30", headers=admin_headers).json()

        assert data["first_recorded_day"] is not None
        assert data["first_recorded_day"] <= data["end_day"]


class TestSayacDayaniklilik:
    def test_counter_failure_does_not_break_request(self, client, student, monkeypatch):
        def _broken_session():
            raise RuntimeError("sayaç için session açılamadı")

        monkeypatch.setattr(metrics, "SessionLocal", _broken_session)
        resp = client.post(
            "/auth/login", json={"email": student["email"], "password": DEFAULT_PASSWORD}
        )
        assert resp.status_code == 200, resp.text

    def test_counter_failure_does_not_break_review_creation(
        self, client, student_headers, course_professor, fake_ai_service, monkeypatch
    ):
        def _broken_session():
            raise RuntimeError("sayaç için session açılamadı")

        monkeypatch.setattr(metrics, "SessionLocal", _broken_session)
        resp = client.post(
            "/reviews", json=review_payload(course_professor.id, AI_TEST_APPROVE), headers=student_headers
        )
        assert resp.status_code == 201, resp.text

    def test_counter_commits_outside_caller_transaction(self, db_session, real_metrics_session):
        event = _SentinelEvent()
        real_metrics_session.append(event.value)

        metrics.increment(event)

        assert _counter_count(event.value) == 1

    def test_second_increment_accumulates_on_same_row(self, db_session, real_metrics_session):
        event = _SentinelEvent()
        real_metrics_session.append(event.value)

        metrics.increment(event)
        metrics.increment(event)

        assert _counter_count(event.value) == 2


class TestYetki:
    @pytest.mark.parametrize("path", ["/admin/stats", "/admin/stats/events"])
    def test_student_is_rejected(self, client, student_headers, path):
        assert client.get(path, headers=student_headers).status_code == 403

    @pytest.mark.parametrize("path", ["/admin/stats", "/admin/stats/events"])
    def test_anonymous_is_rejected(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", ["/admin/stats", "/admin/stats/events"])
    def test_unverified_admin_is_rejected(self, client, db_session, admin, admin_headers, path):
        admin["user"].is_verified = False
        db_session.commit()
        assert client.get(path, headers=admin_headers).status_code == 403
