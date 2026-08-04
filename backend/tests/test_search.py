"""Arama uçlarının Türkçe harf katlaması (`api/common.py: search_filter`).

Sorun: Postgres `lower('I')` = 'i', 'ı' değil (DB collation'ı en_US.UTF-8). Ters yönde ısırıyordu —
`'MİMARLIK' ILIKE '%mimarlik%'` (ASCII yazım) eşleşiyor ama `'%mimarlık%'` (doğru Türkçe yazım)
eşleşmiyordu; yani kullanıcı adı doğru yazdıkça sonuç bulamıyordu. Ölçülen etki: 219 aktif
üniversitenin 59'unda ad büyük `I` içeriyor (ADIYAMAN, IĞDIR, ISPARTA…).

Çözüm her iki tarafı ASCII'ye katlamak; bu dosya beş arama ucunun da o yoldan geçtiğini
doğrular — biri atlanırsa (yeni uç eklenip `search_filter` kullanılmazsa) burada yakalanır.
"""
import uuid

import pytest

from app.api.common import tr_fold
from app.models.course import Course, CourseDepartment
from app.models.professor import Professor
from app.models.university import University


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


class TestTrFold:
    @pytest.mark.parametrize(
        "girdi, beklenen",
        [
            ("IŞIK", "isik"),
            ("ışık", "isik"),
            ("İSTANBUL", "istanbul"),
            ("istanbul", "istanbul"),
            ("MİMARLIK", "mimarlik"),
            ("mimarlık", "mimarlik"),
            ("ÇĞÖŞÜ", "cgosu"),
            ("çğöşü", "cgosu"),
        ],
    )
    def test_katlama(self, girdi, beklenen):
        assert tr_fold(girdi) == beklenen

    def test_farkli_yazimlar_ayni_anahtara_duser(self):
        assert tr_fold("IŞIK") == tr_fold("ışık") == tr_fold("Işık") == tr_fold("isik")


class TestUniversiteAramasi:
    def test_dogru_turkce_yazim_buyuk_harfli_kaydi_bulur(self, client, db_session):
        ek = _suffix()
        db_session.add(University(name=f"IŞIK ÜNİVERSİTESİ-{ek}", city="İstanbul"))
        db_session.commit()

        # Düzeltmeden önce bu arama 0 sonuç dönüyordu: lower('I') = 'i' != 'ı'.
        resp = client.get("/universities", params={"search": f"ışık üniversitesi-{ek}"})
        assert resp.status_code == 200
        assert [u["name"] for u in resp.json()["items"]] == [f"IŞIK ÜNİVERSİTESİ-{ek}"]

    @pytest.mark.parametrize("yazim", ["IĞDIR", "ığdır", "Iğdır", "igdir"])
    def test_butun_yazimlar_ayni_kaydi_bulur(self, client, db_session, yazim):
        ek = _suffix()
        db_session.add(University(name=f"IĞDIR ÜNİVERSİTESİ-{ek}", city="Iğdır"))
        db_session.commit()

        resp = client.get("/universities", params={"search": f"{yazim} üniversitesi-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_kisaltmada_da_katlanir(self, client, db_session):
        ek = _suffix()
        db_session.add(University(name=f"Test Üniversitesi-{ek}", short_name=f"IŞIK{ek}", city="Denizli"))
        db_session.commit()

        resp = client.get("/universities", params={"search": f"ışık{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1


class TestDigerUclar:
    def test_fakulte(self, client, db_session, valid_university):
        from app.models.faculty import Faculty

        ek = _suffix()
        db_session.add(Faculty(university_id=valid_university.id, name=f"IŞIK FAKÜLTESİ-{ek}"))
        db_session.commit()

        resp = client.get("/faculties", params={"university_id": valid_university.id, "search": f"ışık fakültesi-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_bolum_duz_liste(self, client, db_session, valid_faculty):
        from app.models.department import Department

        ek = _suffix()
        db_session.add(Department(faculty_id=valid_faculty.id, name=f"IŞIK MÜHENDİSLİĞİ-{ek}"))
        db_session.commit()

        resp = client.get("/departments", params={"faculty_id": valid_faculty.id, "search": f"ışık mühendisliği-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_bolum_gruplama_dali(self, client, db_session, valid_faculty):
        from app.models.department import Department

        ek = _suffix()
        db_session.add(Department(faculty_id=valid_faculty.id, name=f"IŞIK MÜHENDİSLİĞİ-{ek}"))
        db_session.commit()

        # faculty_id yok -> SQL'de isim bazlı gruplama dalı; o dal da katlamadan geçmeli.
        resp = client.get("/departments", params={"search": f"ışık mühendisliği-{ek}"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1 and items[0]["department_name"] == f"IŞIK MÜHENDİSLİĞİ-{ek}"

    def test_ders_adi(self, client, db_session, valid_department):
        ek = _suffix()
        course = Course(
            university_id=valid_department.faculty.university_id,
            name=f"IŞIK TEKNOLOJİLERİ-{ek}",
            code=f"IST{ek}",
        )
        db_session.add(course)
        db_session.flush()
        db_session.add(CourseDepartment(course_id=course.id, department_id=valid_department.id))
        db_session.commit()

        resp = client.get("/courses", params={"search": f"ışık teknolojileri-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_ders_kodu(self, client, db_session, valid_department):
        ek = _suffix()
        course = Course(
            university_id=valid_department.faculty.university_id,
            name=f"Test Dersi-{ek}",
            code=f"IŞIK{ek}",
        )
        db_session.add(course)
        db_session.flush()
        db_session.add(CourseDepartment(course_id=course.id, department_id=valid_department.id))
        db_session.commit()

        resp = client.get("/courses", params={"search": f"ışık{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_hoca(self, client, db_session):
        ek = _suffix()
        db_session.add(Professor(full_name=f"IŞIL YILMAZ-{ek}"))
        db_session.commit()

        resp = client.get("/professors", params={"search": f"ışıl yılmaz-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1


class TestKacisKorundu:
    def test_yuzde_isareti_hala_literal(self, client, db_session):
        """Katlama `like_pattern` kaçışını bozmamalı: `%` joker değil literal."""
        ek = _suffix()
        db_session.add(University(name=f"Yüzde %50 Üniversitesi-{ek}", city="Denizli"))
        db_session.commit()

        resp = client.get("/universities", params={"search": f"%50 üniversitesi-{ek}"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

        resp = client.get("/universities", params={"search": "%%%%%%"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
