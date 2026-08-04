"""Uçtan uca duman testi: GERÇEK seed verisi + GERÇEK konfigürasyonla tek zincir.

Diğer test dosyalarından farkı ve varlık sebebi: hepsi uydurma fixture verisiyle çalışır
(rastgele adlı "Test Üniversitesi-ab12") ve conftest'teki autouse fixture register'daki
domain<->üniversite kontrolünü kapatır. Sonuç: gerçek EMAIL_DOMAIN_UNIVERSITIES haritası
gerçek DB kayıtlarıyla hiçbir testte karşılaşmıyordu — harita "Pamukkale Üniversitesi",
snapshot "PAMUKKALE ÜNİVERSİTESİ" yazdığı için case-sensitive karşılaştırma her kaydı
reddediyordu ve 381 testin hiçbiri görmedi.

Bu dosya parçaların tek tek doğruluğunu değil, zincirin kopmadığını doğrular:
register -> verify-otp -> login -> /users/me -> ders/hoca -> review -> admin onayı -> public.
Detay doğrulaması ilgili test_*.py dosyalarının işidir.

Snapshot yüklü değilse (boş/başka DB) tüm dosya skip edilir.
"""
import pytest

from conftest import AI_TEST_APPROVE, _create_user, register_payload
from app.core.security import EMAIL_DOMAIN_UNIVERSITIES, tr_casefold
from app.models.course import Course, CourseDepartment
from app.models.course_professor import CourseProfessor
from app.models.department import Department
from app.models.enums import UserRole
from app.models.faculty import Faculty
from app.models.university import University


@pytest.fixture()
def real_data(db_session):
    """Gerçek haritadaki üniversiteyi ve altında yorum yazılabilecek bir (bölüm, ders, cp)
    üçlüsünü DB'den bulur. Sabit id yazılmaz: DB yeniden kurulursa id'ler değişebilir,
    üstelik aranan şey zaten "haritanın DB'de karşılığı var mı" sorusunun kendisi."""
    domain, mapped_name = next(iter(EMAIL_DOMAIN_UNIVERSITIES.items()))

    university = next(
        (
            u
            for u in db_session.query(University).filter(University.deleted_at.is_(None)).all()
            if tr_casefold(u.name) == tr_casefold(mapped_name)
        ),
        None,
    )
    if university is None:
        pytest.skip(f"Seed verisi yüklü değil: '{mapped_name}' bulunamadı")

    row = (
        db_session.query(Department.id, CourseProfessor.id, Course.id)
        .join(Faculty, Department.faculty_id == Faculty.id)
        .join(CourseDepartment, CourseDepartment.department_id == Department.id)
        .join(Course, Course.id == CourseDepartment.course_id)
        .join(CourseProfessor, CourseProfessor.course_id == Course.id)
        .filter(
            Faculty.university_id == university.id,
            Faculty.deleted_at.is_(None),
            Department.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        )
        .order_by(Department.id, Course.id, CourseProfessor.id)
        .first()
    )
    if row is None:
        pytest.skip(f"'{university.name}' altında hocalı ders yok")

    department_id, course_professor_id, course_id = row
    return {
        "domain": domain,
        "university": university,
        "department_id": department_id,
        "course_id": course_id,
        "course_professor_id": course_professor_id,
    }


@pytest.fixture()
def real_domain_check(monkeypatch):
    """conftest'in autouse fixture'ı kontrolü kapatıyor; duman testinin tek anlamı
    gerçek haritayla koşmak olduğu için geri açılır."""
    from app.api import auth as auth_module

    monkeypatch.setattr(auth_module, "EMAIL_DOMAIN_UNIVERSITIES", dict(EMAIL_DOMAIN_UNIVERSITIES))


class TestUctanUcaAkis:
    def test_kayit_giris_yorum_onay_zinciri(
        self, client, db_session, real_data, real_domain_check, otp_capture, fake_ai_service
    ):
        payload = register_payload(real_data["department_id"])

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200, resp.text
        otp = otp_capture["verification"]

        resp = client.post("/auth/verify-otp", json={"email": payload["email"], "otp": otp})
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"]

        resp = client.post(
            "/auth/login", json={"email": payload["email"], "password": payload["password"]}
        )
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 200, resp.text
        me = resp.json()
        assert me["department_id"] == real_data["department_id"]
        assert me["university_id"] == real_data["university"].id
        assert me["university_name"] == real_data["university"].name
        assert 0 <= me["current_grade"] <= 6

        resp = client.get(f"/courses?department_id={real_data['department_id']}")
        assert resp.status_code == 200, resp.text
        courses = resp.json()["items"]
        assert courses, "Gerçek bölümün ders listesi boş dönmemeli"
        # Müfredat verisi seed'de doldurulmuştu; NULL'a düşerse seed/şema uyuşmazlığı var.
        assert any(c["semesters"] and c["is_elective"] is not None for c in courses)

        resp = client.get(f"/course-professors?course_id={real_data['course_id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["items"], "Hocası olan dersin eşleşme listesi boş dönmemeli"

        resp = client.post(
            "/reviews",
            headers=headers,
            json={
                "course_professor_id": real_data["course_professor_id"],
                "teaching_score": 5,
                "difficulty_score": 3,
                "fairness_score": 4,
                "comment": f"{AI_TEST_APPROVE} gerçek veri duman testi",
            },
        )
        assert resp.status_code == 201, resp.text
        review_id = resp.json()["id"]

        resp = client.get("/reviews/me", headers=headers)
        assert resp.status_code == 200, resp.text
        assert any(r["id"] == review_id for r in resp.json()["items"])

        admin = _create_user(db_session, real_data["department_id"], role=UserRole.admin)
        resp = client.post(
            "/auth/login", json={"email": admin["email"], "password": admin["password"]}
        )
        assert resp.status_code == 200, resp.text
        admin_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = client.patch(
            f"/reviews/{review_id}/status", headers=admin_headers, json={"status": "approved"}
        )
        assert resp.status_code == 200, resp.text

        resp = client.get(f"/reviews?course_professor_id={real_data['course_professor_id']}")
        assert resp.status_code == 200, resp.text
        assert any(r["id"] == review_id for r in resp.json()["items"])
