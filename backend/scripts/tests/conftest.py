"""
Ortak test altyapısı.

Tasarım kararları (bkz. CLAUDE.md §10):
- Ayrı bir test veritabanı KURULMUYOR: .env'deki DATABASE_URL, alembic ile migrate edilmiş
  var olan (dev) veritabanına bağlanır. İzolasyon şema seviyesinde değil, HER TEST kendi
  bağlantısını açıp bir transaction+SAVEPOINT içinde çalışır ve test bitince rollback edilir.
  Bu yüzden testler veritabanına kalıcı hiçbir satır bırakmaz (create_all/drop_all yok).
- `client` fixture'ı `get_db` dependency'sini bu transactional session ile override eder;
  böylece hem test kodu hem endpoint kodu AYNI session/transaction üzerinde çalışır.
- Rate limiting (slowapi) varsayılan olarak TÜM testlerde kapalıdır (autouse fixture);
  sadece rate-limit'i özel olarak test eden testler `enable_rate_limiting` fixture'ını
  parametre olarak isteyip kendi içinde açar.
- AI moderasyonu gerçek HuggingFace servisine gitmez: `fake_ai_service` fixture'ı
  `analyze_review_with_hf`'i monkeypatch'ler ve yorum metnindeki işaretleyicilere göre
  (AI_TEST_APPROVE/REJECT/UNCERTAIN/SERVER_ERROR/TIMEOUT/MALFORMED) deterministik sonuç döner.
  İşaretleyici yoksa PENDING döner (diğer review testlerinin AI'dan etkilenmemesi için).
  UNCERTAIN de PENDING döndürür: teknik hata bandından ayırt edilemez, ayrımı senaryo okunur
  kalsın diye taşır. Eşiklerin kendisi test_moderation.py'de gerçek kodla test edilir.

Gereksinimler: pytest, .env dosyasında geçerli bir DATABASE_URL (migrate edilmiş), backend
bu .env ile ayakta OLMASINA gerek yok (testler uygulamayı ayrı process olarak başlatmaz,
doğrudan TestClient ile in-process çalıştırır) ama config aynı .env'den okunur.

Çalıştırma (dizin backend/ olmalı — app/core/config.py .env'i relative arar, scripts/ içinden
çalıştırılırsa DATABASE_URL/SECRET_KEY/EMAIL_PEPPER_KEY "Field required" verir):
    cd backend && ../.venv/bin/python -m pytest scripts/tests -v
"""
import os
import sys
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

# backend/ klasörünü sys.path'e ekle (main.py ve app/ paketi burada yaşıyor)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import app  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.api import reviews as reviews_module  # noqa: E402
from app.api import auth as auth_module  # noqa: E402
from app.core.security import hash_email, hash_password, hash_otp  # noqa: E402
from app.models.email_verification import EmailVerification  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.university import University  # noqa: E402
from app.models.faculty import Faculty  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.course import Course, CourseDepartment  # noqa: E402
from app.models.professor import Professor  # noqa: E402
from app.models.course_professor import CourseProfessor  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import ai_service  # noqa: E402
from app.services import metrics  # noqa: E402
from app.services.moderation import ModerationStatus  # noqa: E402

DEFAULT_PASSWORD = "sifre123"


# ---------------------------------------------------------------------------
# DB / client
# ---------------------------------------------------------------------------

def _joined_session_factory(connection):
    """Verilen connection'a, dıştaki transaction'ı bozmadan (SAVEPOINT ile) "katılan"
    session'lar üreten bir factory döner. Hem test kodunun kullandığı `db_session` hem de
    reviews.py'nin arka plan AI moderasyon task'ının kendi `SessionLocal()` çağrısı AYNI
    connection'a bu şekilde bağlanır — aksi halde background task, testin henüz commit
    etmediği (rollback'e kalmış) review satırını göremez."""

    def _make():
        session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
        session.begin_nested()

        @event.listens_for(session, "after_transaction_end")
        def _restart_savepoint(sess, trans):
            if trans.nested and not trans._parent.nested:
                sess.begin_nested()

        return session

    return _make


@pytest.fixture()
def db_connection():
    connection = engine.connect()
    outer_transaction = connection.begin()
    try:
        yield connection
    finally:
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def db_session(db_connection):
    session = _joined_session_factory(db_connection)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, db_connection, monkeypatch):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(reviews_module, "SessionLocal", _joined_session_factory(db_connection))

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    """Rate limiting testleri dışında slowapi'nin devreye girmemesi için."""
    limiter.enabled = False
    yield
    limiter.enabled = False


@pytest.fixture(autouse=True)
def _disable_email_domain_university_check(monkeypatch):
    """Register'daki e-posta domain'i <-> üniversite eşleşme kontrolü varsayılan olarak kapalı:
    fixture'lar rastgele adlı test üniversiteleri kurar, gerçek harita ("Pamukkale Üniversitesi")
    hepsini reddederdi. Kontrolü test eden testler auth_module üzerinden kendi haritasını yazar.
    Şema tarafındaki domain doğrulaması (is_valid_edu_tr_email) bundan etkilenmez, açık kalır."""
    monkeypatch.setattr(auth_module, "EMAIL_DOMAIN_UNIVERSITIES", {})


class _NullSession:
    """metrics.increment() bunu alırsa hiçbir şey yazmaz."""

    def execute(self, *args, **kwargs):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _isolate_metrics(request, monkeypatch):
    """Olay sayacı kendi SessionLocal'ını açıp COMMIT eder (bilinçli: sayaç isteğin
    transaction'ına bağlı değil) — testte gerçek dev DB'ye kalıcı satır bırakırdı.
    DB kullanan testlerde testin connection'ına bağlanır, DB'ye hiç bağlanmayan
    testlerde (test_moderation.py) sayaç hiç yazılmaz."""
    if "db_connection" in request.fixturenames:
        monkeypatch.setattr(
            metrics, "SessionLocal", _joined_session_factory(request.getfixturevalue("db_connection"))
        )
    else:
        monkeypatch.setattr(metrics, "SessionLocal", _NullSession)


@pytest.fixture()
def real_metrics_session(_isolate_metrics, monkeypatch):
    """`_isolate_metrics`'i geri alır: sayaç gerçekten kendi bağlantısını açıp COMMIT eder.
    Yazılan satır dev DB'de kalıcı olur, `written`'a eklenen olay adları fixture çıkarken
    silinir. `_isolate_metrics`'e bağımlı ki patch sırası garanti olsun."""
    from app.db.session import SessionLocal as RealSessionLocal
    from app.models.event_counter import EventDailyCounter

    monkeypatch.setattr(metrics, "SessionLocal", RealSessionLocal)
    written: list = []
    yield written

    if written:
        cleanup = RealSessionLocal()
        try:
            cleanup.query(EventDailyCounter).filter(
                EventDailyCounter.event.in_(written)
            ).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


@pytest.fixture()
def enable_rate_limiting():
    """Sadece rate limiting'i özel olarak test eden testler bunu ister."""
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False


# ---------------------------------------------------------------------------
# Hiyerarşi fixture'ları: Üniversite -> Fakülte -> Bölüm -> Ders -> Hoca -> CourseProfessor
# ---------------------------------------------------------------------------

def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def valid_university(db_session) -> University:
    uni = University(name=_unique("Test Üniversitesi"), short_name="TEST", city="Denizli")
    db_session.add(uni)
    db_session.commit()
    db_session.refresh(uni)
    return uni


@pytest.fixture()
def valid_faculty(db_session, valid_university) -> Faculty:
    faculty = Faculty(university_id=valid_university.id, name=_unique("Test Fakültesi"))
    db_session.add(faculty)
    db_session.commit()
    db_session.refresh(faculty)
    return faculty


@pytest.fixture()
def valid_department(db_session, valid_faculty) -> Department:
    department = Department(faculty_id=valid_faculty.id, name=_unique("Test Bölümü"))
    db_session.add(department)
    db_session.commit()
    db_session.refresh(department)
    return department


@pytest.fixture()
def make_course(db_session):
    """Kanonik ders + bölüm bağı birlikte açar (ders artık üniversiteye bağlı, §ders kimliği)."""
    def _make(department, name=None, code=None, semesters=None, is_elective=None) -> Course:
        course = Course(
            university_id=department.faculty.university_id,
            name=name or _unique("Test Dersi"),
            code=code or _unique("TST"),
        )
        db_session.add(course)
        db_session.flush()
        db_session.add(
            CourseDepartment(
                course_id=course.id,
                department_id=department.id,
                semesters=semesters,
                is_elective=is_elective,
            )
        )
        db_session.commit()
        db_session.refresh(course)
        return course

    return _make


@pytest.fixture()
def valid_course(valid_department, make_course) -> Course:
    return make_course(valid_department)


@pytest.fixture()
def valid_professor(db_session) -> Professor:
    professor = Professor(full_name=_unique("Test Hoca"))
    db_session.add(professor)
    db_session.commit()
    db_session.refresh(professor)
    return professor


@pytest.fixture()
def course_professor(db_session, valid_course, valid_professor) -> CourseProfessor:
    cp = CourseProfessor(
        course_id=valid_course.id,
        professor_id=valid_professor.id,
        term="2025-Güz",
    )
    db_session.add(cp)
    db_session.commit()
    db_session.refresh(cp)
    return cp


# ---------------------------------------------------------------------------
# Kullanıcı / auth fixture'ları
# ---------------------------------------------------------------------------

def register_payload(department_id: int, **overrides) -> dict:
    payload = {
        "email": f"{_unique('user')}@posta.pau.edu.tr",
        "password": DEFAULT_PASSWORD,
        "department_id": department_id,
        "enrollment_year": date.today().year,
    }
    payload.update(overrides)
    return payload


def _create_user(db_session, department_id, role=UserRole.student, password=DEFAULT_PASSWORD, enrollment_year=None):
    """OTP akışını atlayıp doğrudan DB'de doğrulanmış bir kullanıcı oluşturur.
    Dönen dict: user objesi + login için gereken plain email/password."""
    email = f"{_unique('user')}@posta.pau.edu.tr"
    user = User(
        email_hash=hash_email(email),
        hashed_password=hash_password(password),
        is_verified=True,
        role=role,
        department_id=department_id,
        enrollment_year=enrollment_year or date.today().year,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return {"user": user, "email": email, "password": password}


@pytest.fixture()
def student_factory(db_session, valid_department):
    """Her çağrıda yeni bir öğrenci oluşturan factory (aynı course_professor'a birden
    fazla farklı kullanıcının review yazması gereken senaryolar için)."""
    def _make(department_id=None, enrollment_year=None):
        return _create_user(
            db_session,
            department_id or valid_department.id,
            role=UserRole.student,
            enrollment_year=enrollment_year,
        )
    return _make


@pytest.fixture()
def student(student_factory):
    return student_factory()


@pytest.fixture()
def student_headers(client, student):
    resp = client.post("/auth/login", json={"email": student["email"], "password": student["password"]})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_student(student_factory):
    return student_factory()


@pytest.fixture()
def second_student_headers(client, second_student):
    resp = client.post("/auth/login", json={"email": second_student["email"], "password": second_student["password"]})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin(db_session, valid_department):
    return _create_user(db_session, valid_department.id, role=UserRole.admin)


@pytest.fixture()
def admin_headers(client, admin):
    resp = client.post("/auth/login", json={"email": admin["email"], "password": admin["password"]})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth yardımcıları
# ---------------------------------------------------------------------------

@pytest.fixture()
def otp_capture(monkeypatch):
    """auth.py'deki gerçek "mail gönderimi" (print stub'ı) yerine OTP'yi test koduna
    yakalayan bir sahte. `captured["verification"]` / `captured["reset"]` içinde plain OTP olur."""
    captured: dict = {}

    def _fake_send_verification_email(plain_email: str, otp: str) -> None:
        captured["verification"] = otp

    def _fake_send_reset_email(plain_email: str, otp: str) -> None:
        captured["reset"] = otp

    monkeypatch.setattr(auth_module, "send_verification_email", _fake_send_verification_email)
    monkeypatch.setattr(auth_module, "send_reset_email", _fake_send_reset_email)
    return captured


@pytest.fixture()
def expired_verification_factory(db_session):
    """Süresi dolmuş bir EmailVerification satırı oluşturan factory.
    Dönen dict: email/otp/entry — testler otp'yi doğrudan kullanabilir."""
    from datetime import datetime, timedelta, timezone

    def _make(department_id=None, enrollment_year=None, otp="000000"):
        email = f"{_unique('expired')}@posta.pau.edu.tr"
        entry = EmailVerification(
            email_hash=hash_email(email),
            email_plain=email,
            otp_hash=hash_otp(otp),
            hashed_password=hash_password(DEFAULT_PASSWORD),
            department_id=department_id,
            enrollment_year=enrollment_year or date.today().year,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        return {"email": email, "otp": otp, "entry": entry}

    return _make


# ---------------------------------------------------------------------------
# AI moderasyon sahtesi
# ---------------------------------------------------------------------------

AI_TEST_APPROVE = "AI_TEST_APPROVE"
AI_TEST_REJECT = "AI_TEST_REJECT"
AI_TEST_SERVER_ERROR = "AI_TEST_SERVER_ERROR"
AI_TEST_TIMEOUT = "AI_TEST_TIMEOUT"
AI_TEST_MALFORMED = "AI_TEST_MALFORMED"
AI_TEST_UNCERTAIN = "AI_TEST_UNCERTAIN"


@pytest.fixture()
def fake_ai_service(monkeypatch):
    """`moderate_review`'ın çağırdığı `analyze_review_with_hf`'i, gerçek HTTP isteği atmadan,
    yorum metnindeki işaretleyiciye göre deterministik `ModerationStatus` dönecek şekilde
    monkeypatch'ler. İşaretleyici yoksa PENDING döner."""

    async def _fake_analyze(text: str) -> ModerationStatus:
        text = text or ""
        if AI_TEST_APPROVE in text:
            return ModerationStatus.APPROVED
        if AI_TEST_REJECT in text:
            return ModerationStatus.REJECTED
        if AI_TEST_SERVER_ERROR in text:
            raise RuntimeError("simulated HF 500")
        if AI_TEST_TIMEOUT in text:
            raise TimeoutError("simulated HF timeout")
        if AI_TEST_MALFORMED in text:
            raise ValueError("simulated malformed HF response")
        if AI_TEST_UNCERTAIN in text:
            return ModerationStatus.PENDING
        return ModerationStatus.PENDING

    monkeypatch.setattr(ai_service, "analyze_review_with_hf", _fake_analyze)
    yield