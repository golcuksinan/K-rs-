# Deploy Rehberi

Backend'i Docker ile ayağa kaldırma adımları. Uygulama henüz canlıya alınmadı; bu doküman
hazırlığın kendisidir.

## Bileşenler

| Dosya | İşi |
|---|---|
| `backend/Dockerfile` | API imajı (python:3.12-slim, non-root `kursu` kullanıcısı) |
| `backend/docker-entrypoint.sh` | DB'yi bekler → `alembic upgrade head` → uvicorn |
| `docker-compose.yml` | `db` (postgres:16-alpine, named volume) + `api` |
| `.env.example` | compose değişkenleri (kök dizin) |
| `backend/.env.example` | Docker'sız lokal çalıştırma değişkenleri |

## Adımlar

```bash
cp .env.example .env          # proje kökünde
# SECRET_KEY / EMAIL_PEPPER_KEY: openssl rand -hex 32
# POSTGRES_PASSWORD ve ALLOWED_ORIGINS doldurulur
docker compose up -d --build
curl http://localhost:8000/health
```

Migration'lar konteyner açılışında otomatik koşar. Elle koşmak için:

```bash
docker compose run --rm -e RUN_MIGRATIONS=0 api alembic upgrade head
```

## Kararlar ve tuzaklar

- **Tek worker zorunlu.** Rate limiting in-memory (Redis yok) — her uvicorn worker'ı kendi
  sayacını tutar, N worker limiti N katına çıkarır. `CMD`'de `--workers` verilmedi (varsayılan 1).
  `docker compose up --scale api=N` **yapılmamalı**; ölçekleme önce paylaşımlı bir limiter
  backend'i gerektirir.
- **Kapasite (ölçülmedi, tahmin).** Asıl tavan worker değil DB havuzu: `create_engine` varsayılanla
  çağrıldığı için aynı anda 15 sorgu (`pool_size=5 + max_overflow=10`), kabaca 60-120 istek/sn,
  ~300 eşzamanlı aktif kullanıcı. PAÜ ölçeğinde yeterli. Sıkışırsa ilk müdahale havuzu büyütmek
  (`pool_size=20, pool_pre_ping=True`), worker eklemek değil.
- ⚠️ **Rate limit kampüs NAT'ında patlar.** Limitler IP başına (global `20/second;100/minute`); kampüs
  wifi'sinden gelen herkes tek çıkış IP'si paylaşırsa ortak kotaya girer ve içeriden 429 yer.
  Bilinen açık, canlıya çıkmadan çözülmeli (bkz. CLAUDE.md §11).
- **`DATABASE_URL` compose'da üretiliyor**, `.env`'e elle yazılmaz: host `localhost` değil `db`.
  Konteyner içinde `.env` dosyası yoktur (`.dockerignore`); ayarlar ortam değişkeninden okunur.
- **`EMAIL_PEPPER_KEY` rotate edilmez.** Değişirse tüm `users.email_hash` değerleri geçersiz olur,
  mevcut kullanıcılar giriş yapamaz. `SECRET_KEY`'den farklı bir değer olmalı.
- **`ALLOWED_ORIGINS` prod'da daraltılır.** Varsayılan `*` dev davranışıdır. Değer virgülle
  ayrılmış düz string'dir, JSON dizisi değil (`app/core/config.py`).
- **Seed imaja dahil değil.** `backend/scripts/` hem `.gitignore`'da hem `.dockerignore`'da —
  üniversite/PAÜ verisi prod DB'ye ayrıca yüklenir; en pratiği dev DB'den `pg_dump` alıp prod'a
  `psql` ile aktarmak (scriptleri prod'da çalıştırmak öngörülmedi).
- **E-posta gönderimi yok.** `app/services/email_service.py` hâlâ `print()` stub'ı — OTP kodları
  konteyner loglarına düşer. Gerçek SMTP entegrasyonu DevOps tarafında ve canlı kayıt akışının
  önkoşulu. Bu yüzden `.env.example`'a uydurma SMTP anahtarları konmadı.
- **TLS ve reverse proxy kapsam dışı.** `api` konteyneri düz HTTP servis eder; önüne nginx/Caddy
  konacaksa uvicorn'a `--proxy-headers --forwarded-allow-ips=<proxy-ip>` eklenmelidir — yoksa rate
  limit tüm istekleri proxy'nin IP'si sanar.
- **`/docs` (Swagger) prod'da da açık.** MVP için bilinçli; kapatmak gerekirse
  `FastAPI(docs_url=None, redoc_url=None)`.

## Deploy sonrası

```bash
docker compose exec db psql -U kursu -d kursu_db -c "select count(*) from universities;"
docker compose logs -f api
```

Admin kullanıcısı `scripts/make_admin.py` ile açılır — script imajda olmadığı için host'tan prod
`DATABASE_URL`'i verilerek çalıştırılır.
