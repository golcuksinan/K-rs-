"""Router: app/api/courses.py (prefix /courses)

Ders artık kanonik: üniversiteye bağlı, bölüm bağı `course_departments` join tablosunda.
Ders fixture'ları `make_course` üzerinden açılır (conftest.py).
"""


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
        self, client, db_session, make_course, valid_course, valid_department, valid_faculty
    ):
        from app.models.department import Department

        other_department = Department(faculty_id=valid_faculty.id, name="Başka Bölüm")
        db_session.add(other_department)
        db_session.commit()
        db_session.refresh(other_department)
        other_course = make_course(other_department, name="Başka Ders", code="OTH101")

        resp = client.get("/courses", params={"department_id": valid_department.id})
        ids = [c["id"] for c in resp.json()["items"]]
        assert valid_course.id in ids
        assert other_course.id not in ids

    def test_nonexistent_department_returns_404(self, client):
        resp = client.get("/courses", params={"department_id": 999999})
        assert resp.status_code == 404

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


class TestKanonikDers:
    """Ortak ders iki bölümün müfredatındaysa TEK ders satırı (ve tek değerlendirme havuzu)."""

    @staticmethod
    def _ikinci_bolum(db_session, valid_faculty, name="İkinci Bölüm"):
        from app.models.department import Department

        department = Department(faculty_id=valid_faculty.id, name=name)
        db_session.add(department)
        db_session.commit()
        db_session.refresh(department)
        return department

    def test_iki_bolumde_listelenen_ders_tek_satir(
        self, client, db_session, admin_headers, make_course, valid_department, valid_faculty
    ):
        course = make_course(valid_department, name="Ortak Seçmeli", code="ORT101")
        other = self._ikinci_bolum(db_session, valid_faculty)

        resp = client.post(
            "/courses",
            json={"department_id": other.id, "name": "Ortak Seçmeli", "code": "ORT101"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["id"] == course.id

        for department in (valid_department, other):
            ids = [
                c["id"]
                for c in client.get("/courses", params={"department_id": department.id}).json()["items"]
            ]
            assert course.id in ids

    def test_department_count_bolum_sayisini_verir(
        self, client, db_session, admin_headers, make_course, valid_department, valid_faculty
    ):
        course = make_course(valid_department, name="Sayılan Ders", code="CNT201")
        found = next(
            c
            for c in client.get("/courses", params={"department_id": valid_department.id}).json()["items"]
            if c["id"] == course.id
        )
        assert found["department_count"] == 1

        other = self._ikinci_bolum(db_session, valid_faculty, name="Sayaç Bölümü")
        client.post(
            "/courses",
            json={"department_id": other.id, "name": "Sayılan Ders", "code": "CNT201"},
            headers=admin_headers,
        )
        found = next(
            c for c in client.get("/courses", params={"search": "CNT201"}).json()["items"]
            if c["id"] == course.id
        )
        assert found["department_count"] == 2

    def test_department_count_silinmis_bolumu_saymaz(
        self, client, db_session, admin_headers, make_course, valid_department, valid_faculty
    ):
        from sqlalchemy import func

        course = make_course(valid_department, name="Silinen Bölüm Dersi", code="DEL301")
        other = self._ikinci_bolum(db_session, valid_faculty, name="Silinecek Bölüm")
        client.post(
            "/courses",
            json={"department_id": other.id, "name": "Silinen Bölüm Dersi", "code": "DEL301"},
            headers=admin_headers,
        )

        def _department_count():
            items = client.get("/courses", params={"department_id": valid_department.id}).json()["items"]
            return next(c for c in items if c["id"] == course.id)["department_count"]

        assert _department_count() == 2

        other.deleted_at = func.now()
        db_session.commit()

        assert _department_count() == 1

    def test_ayni_bolume_ikinci_kez_baglanamaz(
        self, client, admin_headers, valid_course, valid_department
    ):
        resp = client.post(
            "/courses",
            json={
                "department_id": valid_department.id,
                "name": valid_course.name,
                "code": valid_course.code,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_search_dalinda_bolum_alanlari_null(self, client, valid_course):
        found = next(
            c for c in client.get("/courses", params={"search": valid_course.code}).json()["items"]
            if c["id"] == valid_course.id
        )
        assert found["department_id"] is None
        assert found["faculty_id"] is None
        assert found["semesters"] is None
        assert found["is_elective"] is None


class TestProfessorCount:
    """professor_count = tekil hoca sayısı; hocasız dersleri ayırt etmek için (PAÜ verisinde
    16.253 dersin 5.322'sinde hiç course_professor vardı)."""

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

    def test_attach_existing_course_returns_real_count(
        self, client, admin_headers, db_session, course_professor, valid_course, valid_faculty
    ):
        """Mevcut kanonik derse yeni bölüm bağı eklenirken sayaç 0 değil gerçek değer döner."""
        from app.models.department import Department

        other = Department(faculty_id=valid_faculty.id, name="Sayaç İkinci Bölüm")
        db_session.add(other)
        db_session.commit()

        resp = client.post(
            "/courses",
            json={"department_id": other.id, "name": valid_course.name, "code": valid_course.code},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["professor_count"] == 1
        assert resp.json()["department_count"] == 2

    def test_patch_keeps_existing_count(self, client, admin_headers, course_professor, valid_course):
        resp = client.patch(
            f"/courses/{valid_course.id}", json={"name": "Sayaç Sonrası Ad"}, headers=admin_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["professor_count"] == 1


class TestMufredatAlanlari:
    """semesters + is_elective: EBS ders planından gelen müfredat verisi, (ders, bölüm)
    ikilisine ait. NULL "bilinmiyor" demek — "zorunlu" ile aynı kovaya konmaz."""

    def test_alanlar_yanitta_doner(self, client, make_course, valid_department):
        course = make_course(
            valid_department, name="Müfredatlı Ders", code="MUF101",
            semesters=[3, 4, 6], is_elective=True,
        )
        resp = client.get("/courses", params={"department_id": valid_department.id})
        found = next(c for c in resp.json()["items"] if c["id"] == course.id)
        assert found["semesters"] == [3, 4, 6]
        assert found["is_elective"] is True

    def test_mufredat_verisi_olmayan_derste_null_doner(self, client, valid_course, valid_department):
        resp = client.get("/courses", params={"department_id": valid_department.id})
        found = next(c for c in resp.json()["items"] if c["id"] == valid_course.id)
        assert found["semesters"] is None
        assert found["is_elective"] is None

    def test_secmeli_filtresi(self, client, make_course, valid_department):
        secmeli = make_course(valid_department, name="Seçmeli Ders", code="SEC101", is_elective=True)
        zorunlu = make_course(valid_department, name="Zorunlu Ders", code="ZOR101", is_elective=False)
        resp = client.get(
            "/courses", params={"department_id": valid_department.id, "is_elective": "true"}
        )
        ids = [c["id"] for c in resp.json()["items"]]
        assert secmeli.id in ids
        assert zorunlu.id not in ids

    def test_zorunlu_filtresi(self, client, make_course, valid_department):
        secmeli = make_course(valid_department, name="Seçmeli Ders", code="SEC101", is_elective=True)
        zorunlu = make_course(valid_department, name="Zorunlu Ders", code="ZOR101", is_elective=False)
        resp = client.get(
            "/courses", params={"department_id": valid_department.id, "is_elective": "false"}
        )
        ids = [c["id"] for c in resp.json()["items"]]
        assert zorunlu.id in ids
        assert secmeli.id not in ids

    def test_filtre_verilmezse_ikisi_de_doner(self, client, make_course, valid_course, valid_department):
        secmeli = make_course(valid_department, name="Seçmeli Ders", code="SEC101", is_elective=True)
        zorunlu = make_course(valid_department, name="Zorunlu Ders", code="ZOR101", is_elective=False)
        ids = [c["id"] for c in client.get(
            "/courses", params={"department_id": valid_department.id}
        ).json()["items"]]
        assert {secmeli.id, zorunlu.id, valid_course.id} <= set(ids)

    def test_mufredat_verisi_olmayan_ders_hicbir_filtre_dalinda_donmez(
        self, client, valid_course, valid_department
    ):
        for deger in ("true", "false"):
            resp = client.get(
                "/courses", params={"department_id": valid_department.id, "is_elective": deger}
            )
            assert valid_course.id not in [c["id"] for c in resp.json()["items"]]

    def test_global_aramada_da_uygulanir(self, client, make_course, valid_department):
        """search dalında filtre EXISTS: "en az bir bölümde seçmeli"."""
        secmeli = make_course(valid_department, name="Zeplin Seçmeli", code="ZPL101", is_elective=True)
        zorunlu = make_course(valid_department, name="Zeplin Zorunlu", code="ZPL102", is_elective=False)
        resp = client.get("/courses", params={"search": "Zeplin", "is_elective": "true"})
        ids = [c["id"] for c in resp.json()["items"]]
        assert secmeli.id in ids
        assert zorunlu.id not in ids

    def test_bir_bolumde_secmeliyse_aramada_donuyor(
        self, client, db_session, make_course, valid_department, valid_faculty
    ):
        from app.models.course import CourseDepartment
        from app.models.department import Department

        course = make_course(valid_department, name="Kaptan Ders", code="KPT101", is_elective=False)
        other = Department(faculty_id=valid_faculty.id, name="Kaptan Bölümü")
        db_session.add(other)
        db_session.commit()
        db_session.add(
            CourseDepartment(course_id=course.id, department_id=other.id, is_elective=True)
        )
        db_session.commit()

        for deger in ("true", "false"):
            ids = [
                c["id"]
                for c in client.get(
                    "/courses", params={"search": "Kaptan Ders", "is_elective": deger}
                ).json()["items"]
            ]
            assert course.id in ids


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

    def test_ayni_ad_farkli_kod_yeni_ders_acar(
        self, client, admin_headers, valid_course, valid_department
    ):
        """Kimlik artık (kod, ad): aynı ad farklı kodla ayrı derstir (ALM 103 tuzağı)."""
        resp = client.post(
            "/courses",
            json={"department_id": valid_department.id, "name": valid_course.name, "code": "DIFFCODE"},
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["id"] != valid_course.id


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

    def test_update_duplicate_kod_ad_rejected(
        self, client, admin_headers, make_course, valid_course, valid_department
    ):
        other = make_course(valid_department, name="Çakışacak Ders", code="CAK101")
        resp = client.patch(
            f"/courses/{other.id}",
            json={"name": valid_course.name, "code": valid_course.code},
            headers=admin_headers,
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

    def test_delete_tum_bolumlerden_dusurur(
        self, client, db_session, admin_headers, make_course, valid_department, valid_faculty
    ):
        """Silme etki alanı üniversite geneli: ders kaç bölümdeyse hepsinden düşer."""
        from app.models.course import CourseDepartment
        from app.models.department import Department

        course = make_course(valid_department, name="Silinecek Ortak", code="SIL101")
        other = Department(faculty_id=valid_faculty.id, name="Silme Bölümü")
        db_session.add(other)
        db_session.commit()
        db_session.add(CourseDepartment(course_id=course.id, department_id=other.id))
        db_session.commit()

        client.delete(f"/courses/{course.id}", headers=admin_headers)
        for department in (valid_department, other):
            ids = [
                c["id"]
                for c in client.get("/courses", params={"department_id": department.id}).json()["items"]
            ]
            assert course.id not in ids


class TestGlobalCourseSearch:
    def test_without_department_id_and_without_search_returns_422(self, client):
        assert client.get("/courses").status_code == 422

    def test_short_search_without_department_id_returns_422(self, client):
        assert client.get("/courses", params={"search": "a"}).status_code == 422

    def test_global_search_finds_course_across_departments(
        self, client, valid_course, valid_university
    ):
        resp = client.get("/courses", params={"search": valid_course.name})
        assert resp.status_code == 200
        found = next(c for c in resp.json()["items"] if c["id"] == valid_course.id)
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
