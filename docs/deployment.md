# Yerel Docker Kurulumu

Backend'i Docker Compose ile ayağa kaldırma adımları. Uygulama henüz canlıya alınmadı ve bu
kurulum **prod yolu değildir** — hedef Heroku + Cloudflare, `docs/deploy-plan.md`.

## Bileşenler

| Dosya | İşi |
|---|---|
| `backend/Dockerfile` | API imajı (python:3.14-slim, non-root `kursu` kullanıcısı) |
| `backend/docker-entrypoint.sh` | `alembic upgrade head` → uvicorn |
| `docker-compose.yml` | `db` (postgres:18-alpine, named volume) + `api` |
| `.env.example` | postgres kullanıcı/parola/db ve `API_PORT` (kök dizin) |
| `backend/.env.example` | uygulama ayarları; compose bunu `env_file` ile yükler |

## Adımlar

```bash
cp .env.example .env                  # POSTGRES_PASSWORD doldurulur
cp backend/.env.example backend/.env  # SECRET_KEY / EMAIL_PEPPER_KEY: openssl rand -hex 32
docker compose up -d --build
curl http://localhost:8000/health
```

Migration'lar konteyner açılışında otomatik koşar. Elle koşmak için:

```bash
docker compose run --rm --entrypoint alembic api upgrade head
```

⚠️ Entrypoint DB'nin hazır olmasını **beklemez**; compose'da bunu `db` servisinin healthcheck'i
örter. Compose dışında çalıştırılıyorsa DB önce ayakta olmalı.

## Kararlar ve tuzaklar

- **Tek worker zorunlu.** Rate limiting in-memory (Redis yok) — her uvicorn worker'ı kendi
  sayacını tutar, N worker limiti N katına çıkarır. `CMD`'de `--workers` verilmedi (varsayılan 1).
  `docker compose up --scale api=N` **yapılmamalı**; ölçekleme önce paylaşımlı bir limiter
  backend'i gerektirir.
- **Değişkenlerin tek sahibi vardır.** Kök `.env` yalnızca postgres ve port değişkenlerini taşır;
  uygulama ayarları `backend/.env`'dedir ve compose'a `env_file` ile girer. Tek istisna
  `DATABASE_URL`: compose'da üretilir ve `env_file`'daki değeri ezer, çünkü konteyner içinde host
  `localhost` değil `db`'dir. Aynı anahtarı iki dosyaya yazma — ayrışırlar.
- **`EMAIL_PEPPER_KEY` rotate edilmez.** Değişirse tüm `users.email_hash` değerleri geçersiz olur,
  mevcut kullanıcılar giriş yapamaz. `SECRET_KEY`'den farklı bir değer olmalı.
- **Bu compose prod'a kopyalanmaz.** 5432 host'a açık ve `./backend:/app` bind mount'u imajın
  içeriğini host'taki checkout ile eziyor; ikisi de bilinçli yerel geliştirme tercihi.
- **Seed imaja dahil değil.** `backend/scripts/` hem `.gitignore`'da hem `.dockerignore`'da.
- **E-posta gönderimi yok.** `app/services/email_service.py` hâlâ `print()` stub'ı — OTP kodları
  konteyner loglarına düşer. Bu yüzden `.env.example`'a uydurma SMTP anahtarları konmadı.
- **`/docs` (Swagger) açık.** MVP için bilinçli; kapatmak gerekirse
  `FastAPI(docs_url=None, redoc_url=None)`.
- **Havuz:** `DB_POOL_SIZE=10 + DB_MAX_OVERFLOW=20` → aynı anda 30 sorgu; yereldeki tavanı
  postgres'in `max_connections`'ı (varsayılan 100) belirler. ⚠️ Yönetilen bir DB'de bu sayı
  plandan gelir ve **küçültülmesi** gerekir — Heroku değerleri `docs/deploy-plan.md`'de.
- **TLS ve reverse proxy kapsam dışı.** `api` konteyneri düz HTTP servis eder. Önüne nginx/Caddy
  konacaksa uvicorn'a `--proxy-headers --forwarded-allow-ips=<proxy-ip>` eklenir ve
  `TRUSTED_PROXY_IPS` set edilir; yoksa rate limit tüm istekleri proxy'nin IP'si sanar.
  ⚠️ Bu tavsiye **yalnızca nginx yolu içindir**, Heroku'ya taşınmaz (`docs/deploy-plan.md` §4.5).
- ⚠️ **Rate limit kampüs NAT'ında patlar.** Limitler IP başına; kampüs wifi'sinden gelen herkes
  tek çıkış IP'si paylaşırsa ortak kotaya girer ve içeriden 429 yer. Canlıya çıkmadan
  çözülmeli — problem, çözüm ve uygulama sırası `docs/deploy-plan.md`'de.

## Kurulum sonrası

```bash
docker compose exec db psql -U kursu -d kursu_db -c "select count(*) from universities;"
docker compose logs -f api
```

Admin kullanıcısı `scripts/make_admin.py` ile açılır — script imajda olmadığı için host'tan
`DATABASE_URL` verilerek çalıştırılır.
