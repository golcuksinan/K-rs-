"""Router: app/api/course_professors.py (prefix /course-professors)"""
from sqlalchemy import func

from app.api.course_professors import _latest_term, _parse_term_key
from app.models.course_professor import CourseProfessor
from app.models.professor import Professor
from app.models.review import Review


def _make_pairings(db_session, course_id, professor_id, terms):
    """Verilen dönemler için aynı ders/hoca ikilisine CourseProfessor satırları yazar."""
    pairings = [
        CourseProfessor(course_id=course_id, professor_id=professor_id, term=term)
        for term in terms
    ]
    db_session.add_all(pairings)
    db_session.commit()
    for cp in pairings:
        db_session.refresh(cp)
    return pairings


def _make_review(db_session, user_id, course_professor_id, status, teaching=5, difficulty=3, fairness=4):
    review = Review(
        user_id=user_id,
        course_professor_id=course_professor_id,
        teaching_score=teaching,
        difficulty_score=difficulty,
        fairness_score=fairness,
        comment="test yorumu",
        status=status,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


class TestGetCourseProfessorDetail:
    def test_not_found_returns_404(self, client):
        resp = client.get("/course-professors/999999")
        assert resp.status_code == 404

    def test_no_reviews_returns_null_averages(self, client, course_professor):
        resp = client.get(f"/course-professors/{course_professor.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["average_teaching_score"] is None
        assert body["review_count"] == 0
        assert "reviews" not in body

    def test_averages_computed_only_from_approved_reviews(
        self, client, db_session, course_professor, student, second_student
    ):
        _make_review(db_session, student["user"].id, course_professor.id, "approved", teaching=5, difficulty=1, fairness=5)
        _make_review(db_session, second_student["user"].id, course_professor.id, "pending", teaching=1, difficulty=1, fairness=1)

        resp = client.get(f"/course-professors/{course_professor.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["average_teaching_score"] == 5
        assert body["review_count"] == 1

    def test_reviews_are_not_embedded(
        self, client, db_session, admin_headers, course_professor, student, second_student
    ):
        # Yorum listesi sayfalı uçtan alınır; detay yanıtı review sayısından bağımsız sabit
        # kalmalı, admin için de.
        _make_review(db_session, student["user"].id, course_professor.id, "approved", teaching=4)
        _make_review(db_session, second_student["user"].id, course_professor.id, "pending", teaching=1)

        for headers in ({}, admin_headers):
            resp = client.get(f"/course-professors/{course_professor.id}", headers=headers)
            assert resp.status_code == 200
            body = resp.json()
            assert "reviews" not in body
            assert body["average_teaching_score"] == 4
            assert body["review_count"] == 1

    def test_response_includes_course_and_professor_names(self, client, course_professor, valid_course, valid_professor):
        resp = client.get(f"/course-professors/{course_professor.id}")
        body = resp.json()
        assert body["course_name"] == valid_course.name
        assert body["course_code"] == valid_course.code
        assert body["professor_name"] == valid_professor.full_name
        assert body["term"] == course_professor.term


class TestParseTermKey:
    def test_guz_is_first_season(self):
        assert _parse_term_key("2025-2026 Güz") == (2025, 0)

    def test_bahar_comes_after_guz_and_yillik(self):
        assert _parse_term_key("2025-2026 Bahar") == (2025, 2)

    def test_case_and_whitespace_tolerant(self):
        assert _parse_term_key("2025-2026 GÜZ") == (2025, 0)
        assert _parse_term_key("  2025-2026 Güz  ") == (2025, 0)

    def test_unknown_season_ranks_last_within_year(self):
        assert _parse_term_key("2025-2026 Sonbahar") == (2025, -1)

    def test_seasons_follow_academic_calendar(self):
        terms = ["2024-2025 Yaz", "2024-2025 Bahar", "2024-2025 Güz", "2024-2025 Yıllık"]
        assert sorted(terms, key=_parse_term_key) == [
            "2024-2025 Güz",
            "2024-2025 Yıllık",
            "2024-2025 Bahar",
            "2024-2025 Yaz",
        ]

    def test_latest_term_breaks_equal_keys_by_string(self):
        # Ayrıştırılamayan iki dönem aynı (0, -1) anahtarına düşer; seçim DB satır sırasına
        # kalmasın diye string ile kırılır.
        assert _latest_term(["Bilinmeyen A", "Bilinmeyen B"]) == "Bilinmeyen B"
        assert _latest_term(["Bilinmeyen B", "Bilinmeyen A"]) == "Bilinmeyen B"

    def test_unparsable_format_ranks_last(self):
        assert _parse_term_key("Bilinmeyen") == (0, -1)
        # conftest'in course_professor fixture'ı tam bu formatı kullanıyor
        assert _parse_term_key("2025-Güz") == (0, -1)

    def test_max_selects_latest_term(self):
        terms = ["2023-2024 Güz", "2025-2026 Güz", "2025-2026 Bahar", "Bilinmeyen"]
        assert max(terms, key=_parse_term_key) == "2025-2026 Bahar"


class TestListCourseProfessors:
    def test_requires_course_id(self, client):
        assert client.get("/course-professors").status_code == 422

    def test_nonexistent_course_returns_404(self, client):
        resp = client.get("/course-professors", params={"course_id": 999999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Ders bulunamadı"

    def test_returns_paginated_envelope(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz"])
        resp = client.get("/course-professors", params={"course_id": valid_course.id})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"items", "total", "limit", "offset"}
        assert body["total"] == 1
        assert body["items"][0]["professor_name"] == valid_professor.full_name

    def test_latest_term_selected_when_term_omitted(self, client, db_session, valid_course, valid_professor):
        _make_pairings(
            db_session,
            valid_course.id,
            valid_professor.id,
            ["2023-2024 Güz", "2025-2026 Güz", "2024-2025 Bahar"],
        )
        body = client.get("/course-professors", params={"course_id": valid_course.id}).json()
        assert body["total"] == 1
        assert {item["term"] for item in body["items"]} == {"2025-2026 Güz"}

    def test_bahar_beats_guz_in_same_year(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz", "2025-2026 Bahar"])
        body = client.get("/course-professors", params={"course_id": valid_course.id}).json()
        assert [item["term"] for item in body["items"]] == ["2025-2026 Bahar"]

    def test_yaz_beats_bahar_in_same_year(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Bahar", "2025-2026 Yaz"])
        body = client.get("/course-professors", params={"course_id": valid_course.id}).json()
        assert [item["term"] for item in body["items"]] == ["2025-2026 Yaz"]

    def test_unparsable_term_sorted_last(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["Bilinmeyen Dönem", "2020-2021 Güz"])
        body = client.get("/course-professors", params={"course_id": valid_course.id}).json()
        assert [item["term"] for item in body["items"]] == ["2020-2021 Güz"]

    def test_unparsable_term_selected_when_only_option(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["Bilinmeyen Dönem"])
        body = client.get("/course-professors", params={"course_id": valid_course.id}).json()
        assert [item["term"] for item in body["items"]] == ["Bilinmeyen Dönem"]

    def test_explicit_term_filters(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz", "2024-2025 Güz"])
        body = client.get(
            "/course-professors", params={"course_id": valid_course.id, "term": "2024-2025 Güz"}
        ).json()
        assert [item["term"] for item in body["items"]] == ["2024-2025 Güz"]

    def test_explicit_unknown_term_returns_empty(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz"])
        resp = client.get(
            "/course-professors", params={"course_id": valid_course.id, "term": "1999-2000 Güz"}
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    def test_course_without_pairings_returns_empty(self, client, valid_course):
        resp = client.get("/course-professors", params={"course_id": valid_course.id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_soft_deleted_course_still_lists_pairings(self, client, db_session, valid_course, valid_professor):
        _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz"])
        valid_course.deleted_at = func.now()
        db_session.commit()

        resp = client.get("/course-professors", params={"course_id": valid_course.id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_averages_only_from_approved_reviews(
        self, client, db_session, valid_course, valid_professor, student, second_student
    ):
        cp = _make_pairings(db_session, valid_course.id, valid_professor.id, ["2025-2026 Güz"])[0]
        _make_review(db_session, student["user"].id, cp.id, "approved", teaching=5, difficulty=1, fairness=5)
        _make_review(db_session, second_student["user"].id, cp.id, "pending", teaching=1, difficulty=5, fairness=1)

        item = client.get("/course-professors", params={"course_id": valid_course.id}).json()["items"][0]
        assert item["avg_teaching"] == 5
        assert item["avg_difficulty"] == 1
        assert item["avg_fairness"] == 5

    def test_limit_and_offset(self, client, db_session, valid_course, valid_professor):
        extra = [Professor(full_name=f"{valid_professor.full_name}-{i}") for i in (1, 2)]
        db_session.add_all(extra)
        db_session.commit()
        for professor in extra:
            db_session.refresh(professor)

        ids = []
        for professor_id in [valid_professor.id] + [p.id for p in extra]:
            ids.append(_make_pairings(db_session, valid_course.id, professor_id, ["2025-2026 Güz"])[0].id)

        base = {"course_id": valid_course.id, "limit": 2}
        first = client.get("/course-professors", params={**base, "offset": 0}).json()
        second = client.get("/course-professors", params={**base, "offset": 2}).json()

        assert first["total"] == second["total"] == 3
        assert [item["id"] for item in first["items"]] == sorted(ids)[:2]
        assert [item["id"] for item in second["items"]] == sorted(ids)[2:]


class TestCreateCourseProfessor:
    def _payload(self, course_id, professor_id, term="2025-2026 Güz"):
        return {"course_id": course_id, "professor_id": professor_id, "term": term}

    def test_requires_admin(self, client, valid_course, valid_professor):
        resp = client.post("/course-professors", json=self._payload(valid_course.id, valid_professor.id))
        assert resp.status_code == 401

    def test_forbidden_for_student(self, client, student_headers, valid_course, valid_professor):
        resp = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, valid_professor.id),
            headers=student_headers,
        )
        assert resp.status_code == 403

    def test_create_success_as_admin(self, client, admin_headers, valid_course, valid_professor):
        resp = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, valid_professor.id),
            headers=admin_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["course_id"] == valid_course.id
        assert body["professor_id"] == valid_professor.id
        assert body["term"] == "2025-2026 Güz"

        detail = client.get(f"/course-professors/{body['id']}")
        assert detail.status_code == 200

    def test_invalid_course_id_rejected(self, client, admin_headers, valid_professor):
        resp = client.post(
            "/course-professors",
            json=self._payload(999_999, valid_professor.id),
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_soft_deleted_course_rejected(self, client, db_session, admin_headers, valid_course, valid_professor):
        valid_course.deleted_at = func.now()
        db_session.commit()

        resp = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, valid_professor.id),
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_invalid_professor_id_rejected(self, client, admin_headers, valid_course):
        resp = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, 999_999),
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_duplicate_term_rejected(self, client, admin_headers, valid_course, valid_professor):
        payload = self._payload(valid_course.id, valid_professor.id)
        first = client.post("/course-professors", json=payload, headers=admin_headers)
        assert first.status_code == 201

        second = client.post("/course-professors", json=payload, headers=admin_headers)
        assert second.status_code == 400

    def test_same_pair_different_term_allowed(self, client, admin_headers, valid_course, valid_professor):
        first = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, valid_professor.id, term="2025-2026 Güz"),
            headers=admin_headers,
        )
        second = client.post(
            "/course-professors",
            json=self._payload(valid_course.id, valid_professor.id, term="2025-2026 Bahar"),
            headers=admin_headers,
        )
        assert first.status_code == 201
        assert second.status_code == 201