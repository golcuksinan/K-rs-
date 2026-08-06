"""Router: app/api/reports.py (prefix /reports)"""
from app.models.review import Review
from app.models.course_professor import CourseProfessor


def _create_approved_review(db_session, user_id, course_professor_id):
    review = Review(
        user_id=user_id,
        course_professor_id=course_professor_id,
        teaching_score=4,
        difficulty_score=3,
        fairness_score=5,
        comment="normal",
        status="approved",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


class TestCreateReport:
    def test_requires_auth(self, client, db_session, student, course_professor):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        resp = client.post("/reports", json={"review_id": review.id, "reason": "uygunsuz içerik"})
        assert resp.status_code == 401

    def test_create_success(self, client, db_session, student, second_student_headers, course_professor):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        resp = client.post(
            "/reports", json={"review_id": review.id, "reason": "uygunsuz içerik"}, headers=second_student_headers
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["review_id"] == review.id
        assert body["status"] == "pending"
        assert "reporter_id" not in body

    def test_nonexistent_review_returns_404(self, client, second_student_headers):
        resp = client.post("/reports", json={"review_id": 999999, "reason": "uygunsuz"}, headers=second_student_headers)
        assert resp.status_code == 404

    def test_duplicate_report_by_same_reporter_rejected(
        self, client, db_session, student, second_student_headers, course_professor
    ):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        client.post("/reports", json={"review_id": review.id, "reason": "sebep 1"}, headers=second_student_headers)
        resp = client.post("/reports", json={"review_id": review.id, "reason": "sebep 2"}, headers=second_student_headers)
        assert resp.status_code == 400

    def test_reason_too_short_rejected(self, client, db_session, student, second_student_headers, course_professor):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        resp = client.post("/reports", json={"review_id": review.id, "reason": "ab"}, headers=second_student_headers)
        assert resp.status_code == 422


class TestListPendingReports:
    def test_requires_admin(self, client, second_student_headers):
        resp = client.get("/reports/pending", headers=second_student_headers)
        assert resp.status_code == 403

    def test_returns_pending_reports_oldest_first(
        self, client, db_session, admin_headers, student, second_student_headers, course_professor
    ):
        # (user_id, course_professor_id) tekil; ikinci yorum için ayrı bir ders-hoca kaydı gerekir.
        other_cp = CourseProfessor(
            course_id=course_professor.course_id,
            professor_id=course_professor.professor_id,
            term="2025-Bahar",
        )
        db_session.add(other_cp)
        db_session.commit()

        first_review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        second_review = _create_approved_review(db_session, student["user"].id, other_cp.id)
        first_id = client.post(
            "/reports", json={"review_id": first_review.id, "reason": "sebep"}, headers=second_student_headers
        ).json()["id"]
        second_id = client.post(
            "/reports", json={"review_id": second_review.id, "reason": "sebep"}, headers=second_student_headers
        ).json()["id"]

        # DB'de başka pending rapor olabilir; liste eskiden yeniye sıralı olduğu için bu testin
        # yarattıkları son sayfadadır ve iddia yalnızca onlara kurulur.
        total = client.get("/reports/pending", params={"limit": 1}, headers=admin_headers).json()["total"]
        resp = client.get(
            "/reports/pending", params={"limit": 2, "offset": total - 2}, headers=admin_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert [item["id"] for item in items] == [first_id, second_id]
        assert all(item["status"] == "pending" for item in items)


class TestUpdateReportStatus:
    def test_requires_admin(self, client, second_student_headers):
        resp = client.patch("/reports/1/status", json={"status": "resolved"}, headers=second_student_headers)
        assert resp.status_code == 403

    def test_resolve_report(self, client, db_session, admin_headers, student, second_student_headers, course_professor):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        created = client.post("/reports", json={"review_id": review.id, "reason": "sebep"}, headers=second_student_headers)
        report_id = created.json()["id"]

        resp = client.patch(f"/reports/{report_id}/status", json={"status": "resolved"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_dismiss_report(self, client, db_session, admin_headers, student, second_student_headers, course_professor):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        created = client.post("/reports", json={"review_id": review.id, "reason": "sebep"}, headers=second_student_headers)
        report_id = created.json()["id"]

        resp = client.patch(f"/reports/{report_id}/status", json={"status": "dismissed"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"

    def test_invalid_status_value_rejected(self, client, admin_headers):
        resp = client.patch("/reports/1/status", json={"status": "pending"}, headers=admin_headers)
        assert resp.status_code == 422

    def test_nonexistent_report_returns_404(self, client, admin_headers):
        resp = client.patch("/reports/999999/status", json={"status": "resolved"}, headers=admin_headers)
        assert resp.status_code == 404


class TestListMyReports:
    def test_requires_auth(self, client):
        resp = client.get("/reports/me")
        assert resp.status_code == 401

    def test_returns_only_own_reports(
        self, client, db_session, student, second_student_headers, admin_headers, course_professor
    ):
        review = _create_approved_review(db_session, student["user"].id, course_professor.id)
        client.post("/reports", json={"review_id": review.id, "reason": "sebep"}, headers=second_student_headers)

        mine = client.get("/reports/me", headers=second_student_headers)
        assert mine.status_code == 200
        assert mine.json()["total"] == 1

        # aynı review'ı henüz şikayet etmemiş başka bir kullanıcı için boş liste
        other = client.get("/reports/me", headers=admin_headers)
        assert other.json()["items"] == []