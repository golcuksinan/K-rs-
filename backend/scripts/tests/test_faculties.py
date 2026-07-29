"""Router: app/api/faculties.py (prefix /faculties)"""


class TestListFaculties:
    def test_requires_university_id(self, client):
        resp = client.get("/faculties")
        assert resp.status_code == 422

    def test_list_by_university_id(self, client, valid_faculty, valid_university):
        resp = client.get("/faculties", params={"university_id": valid_university.id})
        assert resp.status_code == 200
        ids = [f["id"] for f in resp.json()["items"]]
        assert valid_faculty.id in ids

    def test_list_search_filter(self, client, valid_faculty, valid_university):
        resp = client.get(
            "/faculties",
            params={"university_id": valid_university.id, "search": valid_faculty.name[:6]},
        )
        assert resp.status_code == 200
        assert any(f["id"] == valid_faculty.id for f in resp.json()["items"])

    def test_list_search_no_match_returns_empty(self, client, valid_faculty, valid_university):
        resp = client.get(
            "/faculties",
            params={"university_id": valid_university.id, "search": "olmayan-bir-kelime-xyz"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_excludes_soft_deleted(self, client, admin_headers, valid_faculty, valid_university):
        client.delete(f"/faculties/{valid_faculty.id}", headers=admin_headers)
        resp = client.get("/faculties", params={"university_id": valid_university.id})
        assert valid_faculty.id not in [f["id"] for f in resp.json()["items"]]

    def test_list_scoped_to_university_does_not_leak_other_university_faculties(
        self, client, db_session, valid_faculty, valid_university
    ):
        from app.models.university import University
        from app.models.faculty import Faculty

        other_uni = University(name="Başka Üni", city="X")
        db_session.add(other_uni)
        db_session.commit()
        db_session.refresh(other_uni)
        other_faculty = Faculty(university_id=other_uni.id, name="Başka Fakülte")
        db_session.add(other_faculty)
        db_session.commit()

        resp = client.get("/faculties", params={"university_id": valid_university.id})
        ids = [f["id"] for f in resp.json()["items"]]
        assert valid_faculty.id in ids
        assert other_faculty.id not in ids


class TestCreateFaculty:
    def test_create_requires_admin(self, client, valid_university):
        resp = client.post("/faculties", json={"university_id": valid_university.id, "name": "Mühendislik"})
        assert resp.status_code == 401

    def test_create_forbidden_for_student(self, client, student_headers, valid_university):
        resp = client.post(
            "/faculties",
            json={"university_id": valid_university.id, "name": "Mühendislik"},
            headers=student_headers,
        )
        assert resp.status_code == 403

    def test_create_success_as_admin(self, client, admin_headers, valid_university):
        resp = client.post(
            "/faculties",
            json={"university_id": valid_university.id, "name": "Mühendislik"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["university_id"] == valid_university.id

    def test_create_invalid_university_id_rejected(self, client, admin_headers):
        resp = client.post(
            "/faculties", json={"university_id": 999999, "name": "Mühendislik"}, headers=admin_headers
        )
        assert resp.status_code == 400

    def test_create_duplicate_name_in_same_university_rejected(self, client, admin_headers, valid_faculty, valid_university):
        resp = client.post(
            "/faculties",
            json={"university_id": valid_university.id, "name": valid_faculty.name},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_same_name_in_different_university_allowed(self, client, db_session, admin_headers, valid_faculty):
        from app.models.university import University

        other_uni = University(name="Başka Üni 2", city="X")
        db_session.add(other_uni)
        db_session.commit()
        db_session.refresh(other_uni)

        resp = client.post(
            "/faculties",
            json={"university_id": other_uni.id, "name": valid_faculty.name},
            headers=admin_headers,
        )
        assert resp.status_code == 201


class TestUpdateFaculty:
    def test_update_name_success(self, client, admin_headers, valid_faculty):
        resp = client.patch(f"/faculties/{valid_faculty.id}", json={"name": "Yeni İsim"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Yeni İsim"

    def test_update_forbidden_for_student(self, client, student_headers, valid_faculty):
        resp = client.patch(f"/faculties/{valid_faculty.id}", json={"name": "X"}, headers=student_headers)
        assert resp.status_code == 403

    def test_update_nonexistent_returns_404(self, client, admin_headers):
        resp = client.patch("/faculties/999999", json={"name": "X"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_to_duplicate_name_rejected(self, client, db_session, admin_headers, valid_faculty, valid_university):
        from app.models.faculty import Faculty

        other = Faculty(university_id=valid_university.id, name="Diğer Fakülte")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        resp = client.patch(f"/faculties/{other.id}", json={"name": valid_faculty.name}, headers=admin_headers)
        assert resp.status_code == 400


class TestDeleteFaculty:
    def test_delete_is_soft_delete(self, client, db_session, admin_headers, valid_faculty):
        resp = client.delete(f"/faculties/{valid_faculty.id}", headers=admin_headers)
        assert resp.status_code == 204

        from app.models.faculty import Faculty
        row = db_session.query(Faculty).filter(Faculty.id == valid_faculty.id).first()
        assert row is not None
        assert row.deleted_at is not None

    def test_delete_forbidden_for_student(self, client, student_headers, valid_faculty):
        resp = client.delete(f"/faculties/{valid_faculty.id}", headers=student_headers)
        assert resp.status_code == 403

    def test_departments_of_deleted_faculty_still_listed(self, client, admin_headers, valid_faculty, valid_department):
        """Bilinçli istisna: üst kayıt (faculty) silinse bile düz liste uçları
        (GET /departments?faculty_id=) alt kayıtları listelemeye devam eder."""
        client.delete(f"/faculties/{valid_faculty.id}", headers=admin_headers)
        resp = client.get("/departments", params={"faculty_id": valid_faculty.id})
        assert resp.status_code == 200
        assert any(d["id"] == valid_department.id for d in resp.json()["items"])