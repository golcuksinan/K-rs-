"""Router: app/api/universities.py (prefix /universities)"""


class TestListUniversities:
    def test_list_search_by_name(self, client, valid_university):
        resp = client.get("/universities", params={"search": valid_university.name[:6]})
        assert resp.status_code == 200
        names = [u["name"] for u in resp.json()["items"]]
        assert valid_university.name in names

    def test_list_search_by_short_name(self, client, valid_university):
        resp = client.get("/universities", params={"search": valid_university.short_name})
        assert resp.status_code == 200
        assert any(u["id"] == valid_university.id for u in resp.json()["items"])

    def test_list_no_search_returns_paginated_envelope(self, client, valid_university):
        resp = client.get("/universities")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"items", "total", "limit", "offset"}
        assert body["total"] >= 1
        assert len(body["items"]) <= body["limit"]

    def test_list_excludes_soft_deleted(self, client, admin_headers, valid_university):
        client.delete(f"/universities/{valid_university.id}", headers=admin_headers)
        resp = client.get("/universities", params={"search": valid_university.name})
        assert valid_university.id not in [u["id"] for u in resp.json()["items"]]

    def test_search_wildcards_match_literally(self, client, db_session, valid_university):
        # `%`/`_` joker değil literal karakter olarak aranır (like_pattern kaçışı).
        import uuid

        from app.models.university import University

        marked = University(name=f"Yüzde %50 Üniversitesi-{uuid.uuid4().hex[:8]}", city="Denizli")
        db_session.add(marked)
        db_session.commit()
        db_session.refresh(marked)

        resp = client.get("/universities", params={"search": "%50 Üniversitesi"})
        ids = [u["id"] for u in resp.json()["items"]]
        assert marked.id in ids
        assert valid_university.id not in ids

    def test_search_only_wildcards_does_not_match_everything(self, client, valid_university):
        resp = client.get("/universities", params={"search": "%%%%%%"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestCreateUniversity:
    def test_create_requires_admin(self, client):
        resp = client.post("/universities", json={"name": "Yeni Üni", "city": "İzmir"})
        assert resp.status_code == 401

    def test_create_forbidden_for_student(self, client, student_headers):
        resp = client.post("/universities", json={"name": "Yeni Üni", "city": "İzmir"}, headers=student_headers)
        assert resp.status_code == 403

    def test_create_success_as_admin(self, client, admin_headers):
        from conftest import _unique

        name = _unique("Yeni Üni")
        resp = client.post(
            "/universities",
            json={"name": name, "short_name": "YU", "city": "İzmir"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == name
        assert body["deleted_at"] is None

    def test_create_duplicate_name_rejected(self, client, admin_headers, valid_university):
        resp = client.post(
            "/universities",
            json={"name": valid_university.name, "city": "İzmir"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_name_reusable_after_soft_delete(self, client, admin_headers, valid_university):
        client.delete(f"/universities/{valid_university.id}", headers=admin_headers)
        resp = client.post(
            "/universities",
            json={"name": valid_university.name, "city": "İzmir"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text


class TestUpdateUniversity:
    def test_update_success_as_admin(self, client, admin_headers, valid_university):
        resp = client.patch(
            f"/universities/{valid_university.id}",
            json={"city": "Ankara"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["city"] == "Ankara"

    def test_update_forbidden_for_student(self, client, student_headers, valid_university):
        resp = client.patch(
            f"/universities/{valid_university.id}", json={"city": "Ankara"}, headers=student_headers
        )
        assert resp.status_code == 403

    def test_update_nonexistent_returns_404(self, client, admin_headers):
        resp = client.patch("/universities/999999", json={"city": "Ankara"}, headers=admin_headers)
        assert resp.status_code == 404

    def test_update_to_duplicate_name_rejected(self, client, db_session, admin_headers, valid_university):
        from conftest import _unique
        from app.models.university import University

        other = University(name=_unique("Diğer Üni"), city="X")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        resp = client.patch(
            f"/universities/{other.id}", json={"name": valid_university.name}, headers=admin_headers
        )
        assert resp.status_code == 400

    def test_update_soft_deleted_returns_404(self, client, admin_headers, valid_university):
        client.delete(f"/universities/{valid_university.id}", headers=admin_headers)
        resp = client.patch(
            f"/universities/{valid_university.id}", json={"city": "Ankara"}, headers=admin_headers
        )
        assert resp.status_code == 404


class TestDeleteUniversity:
    def test_delete_success_as_admin_is_soft_delete(self, client, db_session, admin_headers, valid_university):
        resp = client.delete(f"/universities/{valid_university.id}", headers=admin_headers)
        assert resp.status_code == 204

        from app.models.university import University
        row = db_session.query(University).filter(University.id == valid_university.id).first()
        assert row is not None  # hard delete değil
        assert row.deleted_at is not None

    def test_delete_forbidden_for_student(self, client, student_headers, valid_university):
        resp = client.delete(f"/universities/{valid_university.id}", headers=student_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_returns_404(self, client, admin_headers):
        resp = client.delete("/universities/999999", headers=admin_headers)
        assert resp.status_code == 404