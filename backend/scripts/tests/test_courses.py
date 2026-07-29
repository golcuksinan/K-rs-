"""Router: app/api/courses.py (prefix /courses)"""


class TestListCourses:
    def test_requires_department_id(self, client):
        resp = client.get("/courses")
        assert resp.status_code == 422

    def test_list_by_department_id(self, client, valid_course, valid_department):
        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert resp.status_code == 200
        body = resp.json()["items"]
        assert any(c["id"] == valid_course.id for c in body)
        found = next(c for c in body if c["id"] == valid_course.id)
        assert found["department_name"] == valid_department.name

    def test_search_by_name(self, client, valid_course, valid_department):
        resp = client.get(
            "/courses", params={"department_id": valid_department.id, "search": valid_course.name[:6]}
        )
        assert resp.status_code == 200
        assert any(c["id"] == valid_course.id for c in resp.json()["items"])

    def test_search_by_code(self, client, valid_course, valid_department):
        resp = client.get(
            "/courses", params={"department_id": valid_department.id, "search": valid_course.code}
        )
        assert resp.status_code == 200
        assert any(c["id"] == valid_course.id for c in resp.json()["items"])

    def test_search_no_match_returns_empty(self, client, valid_course, valid_department):
        resp = client.get(
            "/courses",
            params={"department_id": valid_department.id, "search": "olmayan-ders-xyz"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_scoped_to_department_does_not_leak_other_department_courses(
        self, client, db_session, valid_course, valid_department, valid_faculty
    ):
        from app.models.department import Department
        from app.models.course import Course

        other_department = Department(faculty_id=valid_faculty.id, name="Başka Bölüm")
        db_session.add(other_department)
        db_session.commit()
        db_session.refresh(other_department)
        other_course = Course(department_id=other_department.id, name="Başka Ders", code="OTH101")
        db_session.add(other_course)
        db_session.commit()

        resp = client.get("/courses", params={"department_id": valid_department.id})
        ids = [c["id"] for c in resp.json()["items"]]
        assert valid_course.id in ids
        assert other_course.id not in ids

    def test_courses_of_soft_deleted_department_shows_placeholder_name(
        self, client, admin_headers, valid_course, valid_department
    ):
        client.delete(f"/departments/{valid_department.id}", headers=admin_headers)
        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert resp.status_code == 200
        found = next(c for c in resp.json()["items"] if c["id"] == valid_course.id)
        assert found["department_name"] == "Silinmiş Bölüm"

    def test_list_excludes_soft_deleted_course(self, client, admin_headers, valid_course, valid_department):
        client.delete(f"/courses/{valid_course.id}", headers=admin_headers)
        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert valid_course.id not in [c["id"] for c in resp.json()["items"]]


class TestProfessorCount:
    """professor_count = tekil hoca sayısı; hocasız dersleri ayırt etmek için (PAÜ verisinde
    16.253 dersin 5.322'sinde hiç course_professor yok)."""

    @staticmethod
    def _item(resp, course_id):
        return next(c for c in resp.json()["items"] if c["id"] == course_id)

    def test_zero_when_course_has_no_professor(self, client, valid_course, valid_department):
        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert self._item(resp, valid_course.id)["professor_count"] == 0

    def test_counts_assigned_professor(self, client, course_professor, valid_course, valid_department):
        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert self._item(resp, valid_course.id)["professor_count"] == 1

    def test_same_professor_in_two_terms_counted_once(
        self, client, db_session, course_professor, valid_course, valid_professor, valid_department
    ):
        from app.models.course_professor import CourseProfessor

        db_session.add(
            CourseProfessor(course_id=valid_course.id, professor_id=valid_professor.id, term="2024-Güz")
        )
        db_session.commit()

        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert self._item(resp, valid_course.id)["professor_count"] == 1

    def test_two_professors_counted_separately(
        self, client, db_session, course_professor, valid_course, valid_department
    ):
        from app.models.course_professor import CourseProfessor
        from app.models.professor import Professor

        other = Professor(full_name="İkinci Test Hoca")
        db_session.add(other)
        db_session.commit()
        db_session.add(
            CourseProfessor(course_id=valid_course.id, professor_id=other.id, term="2025-Güz")
        )
        db_session.commit()

        resp = client.get("/courses", params={"department_id": valid_department.id})
        assert self._item(resp, valid_course.id)["professor_count"] == 2

    def test_global_search_also_returns_count(self, client, course_professor, valid_course):
        resp = client.get("/courses", params={"search": valid_course.code})
        assert self._item(resp, valid_course.id)["professor_count"] == 1

    def test_create_returns_zero(self, client, admin_headers, valid_department):
        resp = client.post(
            "/courses",
            json={"department_id": valid_department.id, "name": "Sayaç Dersi", "code": "CNT101"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["professor_count"] == 0

    def test_patch_keeps_existing_count(self, client, admin_headers, course_professor, valid_course):
        resp = client.patch(
            f"/courses/{valid_course.id}", json={"name": "Sayaç Sonrası Ad"}, headers=admin_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["professor_count"] == 1


class TestCreateCourse:
    def test_create_requires_admin(self, client, valid_department):
        resp = client.post(
            "/courses", json={"department_id": valid_department.id, "name": "Veri Yapıları", "code": "CENG201"}
        )
        assert resp.status_code == 401

    def test_create_forbidden_for_student(self, client, student_headers, valid_department):
        resp = client.post(
            "/courses",
            json={"department_id": valid_department.id, "name": "Veri Yapıları", "code": "CENG201"},
            headers=student_headers,
        )
        assert resp.status_code == 403

    def test_create_success_as_admin(self, client, admin_headers, valid_department):
        resp = client.post(
            "/courses",
            json={"department_id": valid_department.id, "name": "Veri Yapıları", "code": "CENG201"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["department_id"] == valid_department.id
        assert resp.json()["code"] == "CENG201"

    def test_create_invalid_department_id_rejected(self, client, admin_headers):
        resp = client.post(
            "/courses",
            json={"department_id": 999999, "name": "Veri Yapıları", "code": "CENG201"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_duplicate_name_in_same_department_rejected(self, client, admin_headers, valid_course, valid_department):
        resp = client.post(
            "/courses",
            json={"department_id": valid_department.id, "name": valid_course.name, "code": "DIFFCODE"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_same_name_in_different_department_allowed(
        self, client, db_session, admin_headers, valid_course, valid_faculty
    ):
        from app.models.department import Department

        other_department = Department(faculty_id=valid_faculty.id, name="Başka Bölüm 2")
        db_session.add(other_department)
        db_session.commit()
        db_session.refresh(other_department)

        resp = client.post(
            "/courses",
            json={"department_id": other_department.id, "name": valid_course.name, "code": "DIFFCODE2"},
            headers=admin_headers,
        )
        assert resp.status_code == 201


class TestUpdateCourse:
    def test_update_name_success(self, client, admin_headers, valid_course):
        resp = client.patch(f"/courses/{valid_course.id}", json={"name": "Yeni Ders Adı"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Yeni Ders Adı"

    def test_update_forbidden_for_student(self, client, student_headers, valid_course):
        resp = client.patch(f"/courses/{valid_course.id}", json={"name": "X"}, headers=student_headers)
        assert resp.status_code == 403

    def test_update_nonexistent_returns_404(self, client, admin_headers):
        resp = client.patch("/courses/999999", json={"name": "X"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_invalid_department_id_rejected(self, client, admin_headers, valid_course):
        resp = client.patch(
            f"/courses/{valid_course.id}", json={"department_id": 999999}, headers=admin_headers
        )
        assert resp.status_code == 400

    def test_update_soft_deleted_course_returns_404(self, client, admin_headers, valid_course):
        client.delete(f"/courses/{valid_course.id}", headers=admin_headers)
        resp = client.patch(f"/courses/{valid_course.id}", json={"name": "X"}, headers=admin_headers)
        assert resp.status_code == 404


class TestDeleteCourse:
    def test_delete_is_soft_delete(self, client, db_session, admin_headers, valid_course):
        resp = client.delete(f"/courses/{valid_course.id}", headers=admin_headers)
        assert resp.status_code == 204

        from app.models.course import Course
        row = db_session.query(Course).filter(Course.id == valid_course.id).first()
        assert row is not None
        assert row.deleted_at is not None

    def test_delete_forbidden_for_student(self, client, student_headers, valid_course):
        resp = client.delete(f"/courses/{valid_course.id}", headers=student_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = client.delete("/courses/999999", headers=admin_headers)
        assert resp.status_code == 404

    def test_delete_already_deleted_returns_404(self, client, admin_headers, valid_course):
        client.delete(f"/courses/{valid_course.id}", headers=admin_headers)
        resp = client.delete(f"/courses/{valid_course.id}", headers=admin_headers)
        assert resp.status_code == 404


class TestGlobalCourseSearch:
    def test_without_department_id_and_without_search_returns_422(self, client):
        assert client.get("/courses").status_code == 422

    def test_short_search_without_department_id_returns_422(self, client):
        assert client.get("/courses", params={"search": "a"}).status_code == 422

    def test_global_search_finds_course_across_departments(
        self, client, valid_course, valid_department, valid_faculty, valid_university
    ):
        resp = client.get("/courses", params={"search": valid_course.name})
        assert resp.status_code == 200
        found = next(c for c in resp.json()["items"] if c["id"] == valid_course.id)
        assert found["department_id"] == valid_department.id
        assert found["faculty_id"] == valid_faculty.id
        assert found["faculty_name"] == valid_faculty.name
        assert found["university_id"] == valid_university.id
        assert found["university_name"] == valid_university.name
        assert found["university_short_name"] == valid_university.short_name

    def test_soft_deleted_university_is_masked(
        self, client, admin_headers, valid_course, valid_university
    ):
        resp = client.delete(f"/universities/{valid_university.id}", headers=admin_headers)
        assert resp.status_code == 204

        resp = client.get("/courses", params={"search": valid_course.name})
        found = next(c for c in resp.json()["items"] if c["id"] == valid_course.id)
        assert found["university_name"] == "Silinmiş Üniversite"
        assert found["university_short_name"] is None
        assert found["university_id"] == valid_university.id