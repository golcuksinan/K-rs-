"""Router: app/api/professors.py (prefix /professors)"""
from app.models.review import Review
from app.models.course_professor import CourseProfessor


def _make_review(db_session, user_id, course_professor_id, status, teaching=5):
    review = Review(
        user_id=user_id,
        course_professor_id=course_professor_id,
        teaching_score=teaching,
        difficulty_score=3,
        fairness_score=4,
        comment="test",
        status=status,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


class TestGetProfessorDetail:
    def test_not_found_returns_404(self, client):
        resp = client.get("/professors/999999")
        assert resp.status_code == 404

    def test_no_course_professors_returns_empty_lists(self, client, valid_professor):
        resp = client.get(f"/professors/{valid_professor.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["courses"] == []
        assert "reviews" not in body

    def test_summarizes_multiple_course_professors(
        self, client, db_session, valid_professor, valid_department, student, make_course
    ):
        course_a = make_course(valid_department, name="Ders A", code="A101")
        course_b = make_course(valid_department, name="Ders B", code="B101")

        cp_a = CourseProfessor(course_id=course_a.id, professor_id=valid_professor.id, term="2025-Güz")
        cp_b = CourseProfessor(course_id=course_b.id, professor_id=valid_professor.id, term="2025-Güz")
        db_session.add_all([cp_a, cp_b])
        db_session.commit()
        db_session.refresh(cp_a)
        db_session.refresh(cp_b)

        _make_review(db_session, student["user"].id, cp_a.id, "approved", teaching=5)

        resp = client.get(f"/professors/{valid_professor.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["courses"]) == 2
        course_a_summary = next(c for c in body["courses"] if c["course_id"] == course_a.id)
        assert course_a_summary["average_teaching_score"] == 5
        assert course_a_summary["review_count"] == 1
        assert course_a_summary["terms"] == [{"course_professor_id": cp_a.id, "term": "2025-Güz"}]
        course_b_summary = next(c for c in body["courses"] if c["course_id"] == course_b.id)
        assert course_b_summary["review_count"] == 0

    def test_same_course_multiple_terms_grouped_into_one_entry(
        self, client, db_session, valid_professor, valid_department, student, second_student, make_course
    ):
        course = make_course(valid_department, name="Tek Ders", code="T101")

        cp_guz = CourseProfessor(course_id=course.id, professor_id=valid_professor.id, term="2025-Güz")
        cp_bahar = CourseProfessor(course_id=course.id, professor_id=valid_professor.id, term="2024-Bahar")
        db_session.add_all([cp_guz, cp_bahar])
        db_session.commit()
        db_session.refresh(cp_guz)
        db_session.refresh(cp_bahar)

        _make_review(db_session, student["user"].id, cp_guz.id, "approved", teaching=5)
        _make_review(db_session, second_student["user"].id, cp_bahar.id, "approved", teaching=3)

        resp = client.get(f"/professors/{valid_professor.id}")
        assert resp.status_code == 200
        courses = [c for c in resp.json()["courses"] if c["course_id"] == course.id]
        assert len(courses) == 1
        summary = courses[0]
        assert [t["term"] for t in summary["terms"]] == ["2024-Bahar", "2025-Güz"]
        assert summary["review_count"] == 2
        assert summary["average_teaching_score"] == 4

    def test_reviews_are_not_embedded(
        self, client, db_session, admin_headers, course_professor, valid_professor, student, second_student
    ):
        _make_review(db_session, student["user"].id, course_professor.id, "approved")
        _make_review(db_session, second_student["user"].id, course_professor.id, "rejected")

        for headers in ({}, admin_headers):
            resp = client.get(f"/professors/{valid_professor.id}", headers=headers)
            assert resp.status_code == 200
            assert "reviews" not in resp.json()


class TestListProfessors:
    def test_returns_paginated_envelope(self, client, valid_professor):
        resp = client.get("/professors")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"items", "total", "limit", "offset"}
        assert body["total"] >= 1

    def test_search_matches_and_returns_title(self, client, db_session, valid_professor):
        valid_professor.title = "Prof. Dr."
        db_session.commit()

        resp = client.get("/professors", params={"search": valid_professor.full_name})
        assert resp.status_code == 200
        found = next(p for p in resp.json()["items"] if p["id"] == valid_professor.id)
        assert found["title"] == "Prof. Dr."
        assert found["full_name"] == valid_professor.full_name

    def test_search_no_match_returns_empty(self, client, valid_professor):
        resp = client.get("/professors", params={"search": "olmayan-hoca-xyz"})
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_course_count_and_averages_only_from_approved(
        self, client, db_session, valid_professor, valid_department, student, second_student,
        make_course,
    ):
        course_a = make_course(valid_department, name="Liste Ders A", code="LA101")
        course_b = make_course(valid_department, name="Liste Ders B", code="LB101")

        cp_a = CourseProfessor(course_id=course_a.id, professor_id=valid_professor.id, term="2025-Güz")
        cp_b = CourseProfessor(course_id=course_b.id, professor_id=valid_professor.id, term="2025-Güz")
        db_session.add_all([cp_a, cp_b])
        db_session.commit()
        db_session.refresh(cp_a)
        db_session.refresh(cp_b)

        _make_review(db_session, student["user"].id, cp_a.id, "approved", teaching=4)
        _make_review(db_session, second_student["user"].id, cp_b.id, "pending", teaching=1)

        resp = client.get("/professors", params={"search": valid_professor.full_name})
        found = next(p for p in resp.json()["items"] if p["id"] == valid_professor.id)
        assert found["course_count"] == 2
        assert found["review_count"] == 1
        assert found["average_teaching_score"] == 4

    def test_course_count_excludes_soft_deleted_courses(
        self, client, db_session, valid_professor, valid_department, make_course
    ):
        from sqlalchemy import func

        course_a = make_course(valid_department, name="Sayım Ders A", code="SA101")
        course_b = make_course(valid_department, name="Sayım Ders B", code="SB101")
        db_session.add_all([
            CourseProfessor(course_id=course_a.id, professor_id=valid_professor.id, term="2025-Güz"),
            CourseProfessor(course_id=course_b.id, professor_id=valid_professor.id, term="2025-Güz"),
        ])
        db_session.commit()

        def _course_count():
            items = client.get("/professors", params={"search": valid_professor.full_name}).json()["items"]
            return next(p for p in items if p["id"] == valid_professor.id)["course_count"]

        assert _course_count() == 2

        course_b.deleted_at = func.now()
        db_session.commit()

        assert _course_count() == 1

    def test_limit_and_offset(self, client, valid_professor):
        first = client.get("/professors", params={"limit": 1, "offset": 0}).json()
        second = client.get("/professors", params={"limit": 1, "offset": 1}).json()
        assert len(first["items"]) == 1
        assert len(second["items"]) == 1
        assert first["items"][0]["id"] != second["items"][0]["id"]
        assert first["total"] == second["total"]