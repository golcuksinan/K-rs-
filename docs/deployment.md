# Deploy Rehberi

Backend'i Docker ile ayağa kaldırma adımları. Uygulama henüz canlıya alınmadı; bu doküman
hazırlığın kendisidir.

## Bileşenler

| Dosya | İşi |
|---|---|
| `backend/Dockerfile` | API imajı (python:3.12-slim, non-root `kursu` kullanıcısı) |
| `backend/docker-entrypoint.sh` | DB'yi bekler → `alembic upgrade head` → uvicorn |
| `docker-compose.yml` | `db` (postgres:16-alpine, named volume) + `api` |
| `.env.example` | postgres kullanıcı/parola/db ve `API_PORT` (kök dizin) |
| `backend/.env.example` | uygulama ayarları; compose bunu `env_file` ile yükler |

## Adımlar

```bash
cp .env.example .env                  # POSTGRES_PASSWORD doldurulur
cp backend/.env.example backend/.env  # SECRET_KEY / EMAIL_PEPPER_KEY: openssl rand -hex 32
                                      # ALLOWED_ORIGINS prod'da daraltılır
docker compose up -d --build
curl http://localhost:8000/health
```

Migration'lar konteyner açılışında otomatik koşar. Elle koşmak için:

```bash
docker compose run --rm --entrypoint alembic api upgrade head
```

## Kararlar ve tuzaklar

- **Tek worker zorunlu.** Rate limiting in-memory (Redis yok) — her uvicorn worker'ı kendi
  sayacını tutar, N worker limiti N katına çıkarır. `CMD`'de `--workers` verilmedi (varsayılan 1).
  `docker compose up --scale api=N` **yapılmamalı**; ölçekleme önce paylaşımlı bir limiter
  backend'i gerektirir.
- **Kapasite (ölçülmedi, tahmin).** Asıl tavan worker değil DB havuzu: `pool_size=10 +
  max_overflow=20` ile aynı anda 30 sorgu. PAÜ ölçeğinde yeterli. Sıkışırsa ilk müdahale
  `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`'u büyütmek, worker eklemek değil — postgres'in
  `max_connections`'ı (varsayılan 100) tavanı belirler.
- ⚠️ **Rate limit kampüs NAT'ında patlar.** Limitler IP başına (global `20/second;100/minute`); kampüs
  wifi'sinden gelen herkes tek çıkış IP'si paylaşırsa ortak kotaya girer ve içeriden 429 yer.
  Bilinen açık, canlıya çıkmadan çözülmeli (bkz. CLAUDE.md §11).
- **Değişkenlerin tek sahibi vardır.** Kök `.env` yalnızca postgres ve port değişkenlerini taşır;
  uygulama ayarları `backend/.env`'dedir ve compose'a `env_file` ile girer. Tek istisna
  `DATABASE_URL`: compose'da üretilir ve `env_file`'daki değeri ezer, çünkü konteyner içinde host
  `localhost` değil `db`'dir. Aynı anahtarı iki dosyaya yazma — ayrışırlar.
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
