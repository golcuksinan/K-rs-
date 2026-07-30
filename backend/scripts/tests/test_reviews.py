"""Router: app/api/reviews.py (prefix /reviews)

AI moderasyon senaryoları `fake_ai_service` fixture'ı ile deterministik hale getirilir
(bkz. conftest.py) — yorum metnine AI_TEST_APPROVE/REJECT/SERVER_ERROR/TIMEOUT/MALFORMED
işaretleyicilerinden biri eklenir. İşaretleyici yoksa sonuç PENDING olur.
"""
from conftest import (
    AI_TEST_APPROVE, AI_TEST_REJECT, AI_TEST_SERVER_ERROR, AI_TEST_TIMEOUT, AI_TEST_MALFORMED,
    AI_TEST_UNCERTAIN,
)


def _review_payload(course_professor_id, comment="normal bir yorum", **overrides):
    payload = {
        "course_professor_id": course_professor_id,
        "teaching_score": 4,
        "difficulty_score": 3,
        "fairness_score": 5,
        "comment": comment,
    }
    payload.update(overrides)
    return payload


class TestCreateReview:
    def test_requires_auth(self, client, course_professor):
        resp = client.post("/reviews", json=_review_payload(course_professor.id))
        assert resp.status_code == 401

    def test_create_returns_pending_immediately(self, client, student_headers, course_professor):
        resp = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "pending"

    def test_nonexistent_course_professor_returns_404(self, client, student_headers):
        resp = client.post("/reviews", json=_review_payload(999999), headers=student_headers)
        assert resp.status_code == 404

    def test_duplicate_review_by_same_user_rejected(self, client, student_headers, course_professor):
        client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        resp = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        assert resp.status_code == 400

    def test_soft_deleted_course_rejected(self, client, db_session, student_headers, course_professor, valid_course):
        from sqlalchemy import func

        valid_course.deleted_at = func.now()
        db_session.commit()

        resp = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        assert resp.status_code == 400

    def test_score_out_of_range_rejected(self, client, student_headers, course_professor):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, teaching_score=6), headers=student_headers
        )
        assert resp.status_code == 422

    def test_ai_moderation_approves(self, client, db_session, student_headers, course_professor, fake_ai_service):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "approved"

    def test_ai_moderation_rejects(self, client, db_session, student_headers, course_professor, fake_ai_service):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_REJECT), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "rejected"

    def test_ai_moderation_uncertain_stays_pending_and_enters_admin_queue(
        self, client, db_session, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_UNCERTAIN), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "pending"

        queue = client.get("/reviews/pending", headers=admin_headers)
        assert review_id in [item["id"] for item in queue.json()["items"]]

    def test_ai_moderation_uncertain_not_visible_publicly(
        self, client, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_UNCERTAIN), headers=student_headers
        )
        review_id = resp.json()["id"]

        public = client.get(f"/reviews?course_professor_id={course_professor.id}")
        assert review_id not in [item["id"] for item in public.json()["items"]]

    def test_ai_moderation_server_error_falls_back_to_pending(
        self, client, db_session, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_SERVER_ERROR), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "pending"

    def test_ai_moderation_timeout_falls_back_to_pending(
        self, client, db_session, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_TIMEOUT), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "pending"

    def test_ai_moderation_malformed_response_falls_back_to_pending(
        self, client, db_session, student_headers, course_professor, fake_ai_service
    ):
        resp = client.post(
            "/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_MALFORMED), headers=student_headers
        )
        review_id = resp.json()["id"]

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "pending"


class TestModerationBackgroundRace:
    """Arka plan task'ı yalnızca review hâlâ pending VE moderasyona soktuğu metin değişmemişse
    yazar. Yarış elle kurulur: TestClient'ta background task senkron çalışıyor."""

    @staticmethod
    def _pending_review_id(client, student_headers, course_professor_id):
        created = client.post("/reviews", json=_review_payload(course_professor_id), headers=student_headers)
        assert created.status_code == 201, created.text
        return created.json()["id"]

    def test_admin_decision_is_not_overwritten(
        self, client, db_session, monkeypatch, admin_headers, student_headers, course_professor, fake_ai_service
    ):
        from app.api import reviews as reviews_module
        from app.models.review import Review

        review_id = self._pending_review_id(client, student_headers, course_professor.id)
        approved = client.patch(
            f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers
        )
        assert approved.status_code == 200

        monkeypatch.setattr(reviews_module, "moderate_review", lambda review: "rejected")
        reviews_module._run_moderation_background(review_id)

        db_session.expire_all()
        assert db_session.query(Review).filter(Review.id == review_id).first().status == "approved"

    def test_edit_during_moderation_is_not_overwritten(
        self, client, db_session, monkeypatch, student_headers, course_professor, fake_ai_service
    ):
        from app.api import reviews as reviews_module
        from app.models.review import Review

        review_id = self._pending_review_id(client, student_headers, course_professor.id)

        def _moderate_then_edit(review):
            # HF beklenirken kullanıcı yorumu değiştirdi -> bu task'ın kararı bayat kaldı
            side = reviews_module.SessionLocal()
            side.query(Review).filter(Review.id == review_id).update(
                {"comment": "araya giren düzenleme"}, synchronize_session=False
            )
            side.commit()
            side.close()
            return "approved"

        monkeypatch.setattr(reviews_module, "moderate_review", _moderate_then_edit)
        reviews_module._run_moderation_background(review_id)

        db_session.expire_all()
        assert db_session.query(Review).filter(Review.id == review_id).first().status == "pending"


class TestListReviews:
    def test_public_list_only_shows_approved(self, client, db_session, student_headers, course_professor, fake_ai_service):
        client.post("/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE), headers=student_headers)

        resp = client.get("/reviews")
        assert resp.status_code == 200
        assert all(r["status"] == "approved" for r in resp.json()["items"])

    def test_public_list_excludes_pending_and_rejected(
        self, client, student_headers, second_student_headers, course_professor, fake_ai_service, db_session
    ):
        client.post("/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_REJECT), headers=student_headers)

        resp = client.get("/reviews", params={"course_professor_id": course_professor.id})
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_filter_by_course_professor_id(self, client, db_session, student_headers, course_professor, fake_ai_service):
        client.post("/reviews", json=_review_payload(course_professor.id, comment=AI_TEST_APPROVE), headers=student_headers)
        resp = client.get("/reviews", params={"course_professor_id": course_professor.id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestListPendingReviews:
    def test_requires_admin(self, client, student_headers):
        resp = client.get("/reviews/pending", headers=student_headers)
        assert resp.status_code == 403

    def test_shows_pending_and_edit_requested_reviews(
        self, client, admin_headers, student_headers, course_professor
    ):
        client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        resp = client.get("/reviews/pending", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["status"] == "pending"


class TestUpdateReviewStatus:
    def test_requires_admin(self, client, student_headers, db_session, course_professor):
        resp = client.patch(
            f"/reviews/{1}/status", json={"status": "approved"}, headers=student_headers
        )
        assert resp.status_code in (403, 404)

    def test_approve_pending_review(self, client, admin_headers, student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject_pending_review(self, client, admin_headers, student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(f"/reviews/{review_id}/status", json={"status": "rejected"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_nonexistent_review_returns_404(self, client, admin_headers):
        resp = client.patch("/reviews/999999/status", json={"status": "approved"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_reject_takes_down_review_even_with_pending_edit(
        self, client, admin_headers, student_headers, course_professor
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]
        client.patch(f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers)

        client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "düzenlendi"},
            headers=student_headers,
        )

        resp = client.patch(f"/reviews/{review_id}/status", json={"status": "rejected"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # gölge de temizlendi -> admin kuyruğunda görünmez
        me = client.get("/reviews/me", headers=student_headers)
        assert me.json()["items"][0]["has_pending_edit"] is False


class TestUpdateReviewEditStatus:
    def _approved_review_with_pending_edit(self, client, admin_headers, student_headers, course_professor_id):
        created = client.post("/reviews", json=_review_payload(course_professor_id, teaching_score=5), headers=student_headers)
        review_id = created.json()["id"]
        client.patch(f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers)
        client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "düzenlendi"},
            headers=student_headers,
        )
        return review_id

    def test_requires_admin(self, client, student_headers):
        resp = client.patch("/reviews/1/edit-status", json={"status": "approved"}, headers=student_headers)
        assert resp.status_code in (403, 404)

    def test_nonexistent_review_returns_404(self, client, admin_headers):
        resp = client.patch("/reviews/999999/edit-status", json={"status": "approved"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_without_pending_edit_returns_400(self, client, admin_headers, student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(f"/reviews/{review_id}/edit-status", json={"status": "approved"}, headers=admin_headers)
        assert resp.status_code == 400

    def test_approve_copies_shadow_fields_and_keeps_status_approved(
        self, client, admin_headers, student_headers, course_professor
    ):
        review_id = self._approved_review_with_pending_edit(
            client, admin_headers, student_headers, course_professor.id
        )

        resp = client.patch(f"/reviews/{review_id}/edit-status", json={"status": "approved"}, headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert body["teaching_score"] == 1
        assert body["comment"] == "düzenlendi"
        assert body["has_pending_edit"] is False

    def test_reject_discards_shadow_fields_keeps_original(
        self, client, admin_headers, student_headers, course_professor
    ):
        review_id = self._approved_review_with_pending_edit(
            client, admin_headers, student_headers, course_professor.id
        )

        resp = client.patch(f"/reviews/{review_id}/edit-status", json={"status": "rejected"}, headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"  # orijinal statüye dokunulmadı
        assert body["teaching_score"] == 5  # orijinal değer korundu
        assert body["has_pending_edit"] is False


class TestListMyReviews:
    def test_requires_auth(self, client):
        resp = client.get("/reviews/me")
        assert resp.status_code == 401

    def test_returns_only_own_reviews_newest_first(
        self, client, student_headers, second_student_headers, course_professor, db_session
    ):
        first = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        assert first.status_code == 201

        resp = client.get("/reviews/me", headers=student_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert "has_pending_edit" in resp.json()["items"][0]

        other_resp = client.get("/reviews/me", headers=second_student_headers)
        assert other_resp.json()["items"] == []


class TestUpdateMyReview:
    def test_requires_ownership(self, client, student_headers, second_student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "x"},
            headers=second_student_headers,
        )
        assert resp.status_code == 403

    def test_nonexistent_review_returns_404(self, client, student_headers):
        resp = client.patch(
            "/reviews/999999",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "x"},
            headers=student_headers,
        )
        assert resp.status_code == 404

    def test_editing_pending_review_updates_directly(self, client, student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 2, "difficulty_score": 2, "fairness_score": 2, "comment": "güncellendi"},
            headers=student_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["teaching_score"] == 2
        assert body["status"] == "pending"
        assert body["has_pending_edit"] is False

    def test_editing_pending_review_retriggers_ai_moderation(
        self, client, db_session, student_headers, course_professor, fake_ai_service
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 2, "difficulty_score": 2, "fairness_score": 2,
                  "comment": f"düzenlendi {AI_TEST_APPROVE}"},
            headers=student_headers,
        )

        from app.models.review import Review
        review = db_session.query(Review).filter(Review.id == review_id).first()
        assert review.status == "approved"

    def test_editing_approved_review_creates_pending_edit_without_changing_live_values(
        self, client, admin_headers, student_headers, course_professor
    ):
        created = client.post("/reviews", json=_review_payload(course_professor.id, teaching_score=5), headers=student_headers)
        review_id = created.json()["id"]
        client.patch(f"/reviews/{review_id}/status", json={"status": "approved"}, headers=admin_headers)

        resp = client.patch(
            f"/reviews/{review_id}",
            json={"teaching_score": 1, "difficulty_score": 1, "fairness_score": 1, "comment": "yeni yorum"},
            headers=student_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert body["teaching_score"] == 5  # canlı değer değişmedi
        assert body["has_pending_edit"] is True
        assert body["pending_teaching_score"] == 1
        assert body["pending_comment"] == "yeni yorum"

        # public liste hâlâ eski (onaylı) değeri göstermeli
        public_resp = client.get("/reviews", params={"course_professor_id": course_professor.id})
        public_review = next(r for r in public_resp.json()["items"] if r["id"] == review_id)
        assert public_review["teaching_score"] == 5


class TestDeleteReview:
    def test_requires_ownership(self, client, student_headers, second_student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.delete(f"/reviews/{review_id}", headers=second_student_headers)
        assert resp.status_code == 403

    def test_owner_can_delete(self, client, db_session, student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        resp = client.delete(f"/reviews/{review_id}", headers=student_headers)
        assert resp.status_code == 204

        from app.models.review import Review
        assert db_session.query(Review).filter(Review.id == review_id).first() is None

    def test_deleting_review_also_deletes_its_reports(self, client, db_session, student_headers, second_student_headers, course_professor):
        created = client.post("/reviews", json=_review_payload(course_professor.id), headers=student_headers)
        review_id = created.json()["id"]

        report_resp = client.post(
            "/reports", json={"review_id": review_id, "reason": "uygunsuz içerik"}, headers=second_student_headers
        )
        assert report_resp.status_code == 201

        client.delete(f"/reviews/{review_id}", headers=student_headers)

        from app.models.report import Report
        assert db_session.query(Report).filter(Report.review_id == review_id).count() == 0

    def test_nonexistent_review_returns_404(self, client, student_headers):
        resp = client.delete("/reviews/999999", headers=student_headers)
        assert resp.status_code == 404