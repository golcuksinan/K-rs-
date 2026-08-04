"""Router: app/api/departments.py (prefix /departments)"""


class TestListDepartmentsFlat:
    def test_requires_faculty_id_or_search(self, client):
        resp = client.get("/departments")
        assert resp.status_code == 422

    def test_list_by_faculty_id(self, client, valid_department, valid_faculty):
        resp = client.get("/departments", params={"faculty_id": valid_faculty.id})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["items"], list)
        assert any(d["id"] == valid_department.id for d in body["items"])

    def test_list_by_faculty_id_with_search(self, client, valid_department, valid_faculty):
        resp = client.get(
            "/departments",
            params={"faculty_id": valid_faculty.id, "search": valid_department.name[:6]},
        )
        assert resp.status_code == 200
        assert any(d["id"] == valid_department.id for d in resp.json()["items"])

    def test_list_excludes_soft_deleted_department(self, client, admin_headers, valid_department, valid_faculty):
        client.delete(f"/departments/{valid_department.id}", headers=admin_headers)
        resp = client.get("/departments", params={"faculty_id": valid_faculty.id})
        assert valid_department.id not in [d["id"] for d in resp.json()["items"]]

    def test_flat_list_still_returns_departments_of_deleted_faculty(
        self, client, admin_headers, valid_department, valid_faculty
    ):
        client.delete(f"/faculties/{valid_faculty.id}", headers=admin_headers)
        resp = client.get("/departments", params={"faculty_id": valid_faculty.id})
        assert resp.status_code == 200
        assert any(d["id"] == valid_department.id for d in resp.json()["items"])


class TestListDepartmentsGrouped:
    def test_search_without_faculty_id_groups_by_name(self, client, db_session, valid_department, valid_university):
        from app.models.faculty import Faculty
        from app.models.department import Department

        # Aynı isimde bölüm, FARKLI bir fakültede (bilinçli desen — aynı fakültede aynı isim
        # unique constraint'e takılır, bkz. models/department.py).
        other_faculty = Faculty(university_id=valid_university.id, name="İkinci Fakülte")
        db_session.add(other_faculty)
        db_session.commit()
        db_session.refresh(other_faculty)

        twin = Department(faculty_id=other_faculty.id, name=valid_department.name)
        db_session.add(twin)
        db_session.commit()

        resp = client.get("/departments", params={"search": valid_department.name})
        assert resp.status_code == 200
        groups = resp.json()["items"]
        matching = [g for g in groups if g["department_name"] == valid_department.name]
        assert len(matching) == 1

    def test_grouped_search_shows_deleted_faculty_placeholder(
        self, client, admin_headers, valid_department, valid_faculty
    ):
        client.delete(f"/faculties/{valid_faculty.id}", headers=admin_headers)
        resp = client.get("/departments", params={"search": valid_department.name})
        assert resp.status_code == 200
        groups = [g for g in resp.json()["items"] if g["department_name"] == valid_department.name]
        assert len(groups) == 1
        faculty_names = [f["name"] for f in groups[0]["faculties"]]
        assert "Silinmiş Fakülte" in faculty_names

    def test_grouped_search_no_match_returns_empty_list(self, client, valid_department):
        resp = client.get("/departments", params={"search": "olmayan-bir-bolum-xyz"})
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_limit_offset_applied_at_group_level(self, client, db_session, valid_faculty, valid_university):
        import uuid

        from app.models.department import Department
        from app.models.faculty import Faculty

        token = f"Gruplu{uuid.uuid4().hex[:8]}"
        second_faculty = Faculty(university_id=valid_university.id, name=f"{token} Fakültesi")
        db_session.add(second_faculty)
        db_session.commit()
        db_session.refresh(second_faculty)

        names = [f"{token} Bolum {i}" for i in range(5)]
        db_session.add_all([Department(faculty_id=valid_faculty.id, name=name) for name in names])
        # ilk ad iki fakültede: grup sayısı yine 5, eşleşen satır sayısı 6
        db_session.add(Department(faculty_id=second_faculty.id, name=names[0]))
        db_session.commit()

        first = client.get("/departments", params={"search": token, "limit": 2, "offset": 0}).json()
        assert first["total"] == 5
        assert [g["department_name"] for g in first["items"]] == names[:2]
        assert len(first["items"][0]["faculties"]) == 2

        last = client.get("/departments", params={"search": token, "limit": 2, "offset": 4}).json()
        assert last["total"] == 5
        assert [g["department_name"] for g in last["items"]] == names[4:]

    def test_total_counts_all_matching_groups_not_just_first_page(self, client, db_session):
        """total, sayfa penceresinden değil eşleşen tüm gruplardan sayılır (eski kod ham
        satırları 500'de kırpıp kırpılmış kümenin gruplarını sayıyordu)."""
        from sqlalchemy import distinct, func

        from app.api.common import like_pattern
        from app.models.department import Department

        expected = db_session.query(func.count(distinct(Department.name))).filter(
            Department.name.ilike(like_pattern("a"), escape="\\"),
            Department.deleted_at.is_(None),
        ).scalar()

        body = client.get("/departments", params={"search": "a", "limit": 1}).json()
        assert body["total"] == expected
        assert len(body["items"]) == min(1, expected)


class TestCreateDepartment:
    def test_create_requires_admin(self, client, valid_faculty):
        resp = client.post("/departments", json={"faculty_id": valid_faculty.id, "name": "Bilgisayar Müh."})
        assert resp.status_code == 401

    def test_create_forbidden_for_student(self, client, student_headers, valid_faculty):
        resp = client.post(
            "/departments",
            json={"faculty_id": valid_faculty.id, "name": "Bilgisayar Müh."},
            headers=student_headers,
        )
        assert resp.status_code == 403

    def test_create_success_as_admin(self, client, admin_headers, valid_faculty):
        resp = client.post(
            "/departments",
            json={"faculty_id": valid_faculty.id, "name": "Bilgisayar Müh."},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["faculty_id"] == valid_faculty.id

    def test_create_invalid_faculty_id_rejected(self, client, admin_headers):
        resp = client.post(
            "/departments", json={"faculty_id": 999999, "name": "Bilgisayar Müh."}, headers=admin_headers
        )
        assert resp.status_code == 400

    def test_create_duplicate_name_in_same_faculty_rejected(self, client, admin_headers, valid_department, valid_faculty):
        resp = client.post(
            "/departments",
            json={"faculty_id": valid_faculty.id, "name": valid_department.name},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_create_same_name_in_different_faculty_allowed(self, client, db_session, admin_headers, valid_department, valid_university):
        from app.models.faculty import Faculty

        other_faculty = Faculty(university_id=valid_university.id, name="Başka Fakülte 2")
        db_session.add(other_faculty)
        db_session.commit()
        db_session.refresh(other_faculty)

        resp = client.post(
            "/departments",
            json={"faculty_id": other_faculty.id, "name": valid_department.name},
            headers=admin_headers,
        )
        assert resp.status_code == 201


class TestUpdateDepartment:
    def test_update_name_success(self, client, admin_headers, valid_department):
        resp = client.patch(f"/departments/{valid_department.id}", json={"name": "Yeni Bölüm Adı"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Yeni Bölüm Adı"

    def test_update_forbidden_for_student(self, client, student_headers, valid_department):
        resp = client.patch(f"/departments/{valid_department.id}", json={"name": "X"}, headers=student_headers)
        assert resp.status_code == 403

    def test_update_nonexistent_returns_404(self, client, admin_headers):
        resp = client.patch("/departments/999999", json={"name": "X"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_faculty_id_in_body_is_ignored(
        self, client, db_session, admin_headers, valid_department, valid_faculty, valid_university
    ):
        """Bölüm başka fakülteye taşınamaz: DepartmentUpdate'te faculty_id yok, Pydantic
        alanı yok sayar (taşıma Course.university_id zincirini kırardı)."""
        from app.models.faculty import Faculty

        other = Faculty(university_id=valid_university.id, name="Taşıma Hedefi Fakültesi")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        resp = client.patch(
            f"/departments/{valid_department.id}",
            json={"faculty_id": other.id, "name": "Taşınmayan Bölüm"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["faculty_id"] == valid_faculty.id


class TestDeleteDepartment:
    def test_delete_is_soft_delete(self, client, db_session, admin_headers, valid_department):
        resp = client.delete(f"/departments/{valid_department.id}", headers=admin_headers)
        assert resp.status_code == 204

        from app.models.department import Department
        row = db_session.query(Department).filter(Department.id == valid_department.id).first()
        assert row is not None
        assert row.deleted_at is not None

    def test_delete_forbidden_for_student(self, client, student_headers, valid_department):
        resp = client.delete(f"/departments/{valid_department.id}", headers=student_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = client.delete("/departments/999999", headers=admin_headers)
        assert resp.status_code == 404