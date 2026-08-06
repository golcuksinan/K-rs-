# Deployment

Kürsü'nün deployment belgesi: yerel Docker kurulumu, prod deploy adımları ve ikisinin
gerekçeleri.

Hedef mimari:

```
kursu.live / www.kursu.live   → Cloudflare Pages (statik Vite build'i)
api.kursu.live                → Cloudflare (proxied) → Heroku container dyno → Postgres Essential-0
```

| Kalem | Seçim | Fiyat |
|---|---|---|
| Web dyno | Basic (Cedar) | $7 — 512 MB RAM, 1× paylaşımlı CPU, uyumaz |
| Veritabanı | Postgres Essential-0 | $5 — 1 GB depolama, 20 bağlantı, pgbouncer yok |
| Frontend | Cloudflare Pages | $0 |

Eco dyno reddedildi (30 dk boştaysa uyur), Basic ayrıca ACM sertifikasının önkoşulu.

---

## 1. Yerel Docker kurulumu

Bu kurulum **prod yolu değildir**; compose 5432'yi host'a açar ve `./backend:/app` bind
mount'uyla imajın içeriğini checkout ile ezer — ikisi de bilinçli geliştirme tercihi.

| Dosya | İşi |
|---|---|
| `backend/Dockerfile` | API imajı (python:3.14-slim, non-root `kursu` kullanıcısı) |
| `backend/docker-entrypoint.sh` | `alembic upgrade head` → uvicorn |
| `docker-compose.yml` | `db` (postgres:18-alpine, named volume) + `api` |
| `.env.example` | postgres kullanıcı/parola/db ve `API_PORT` (kök dizin) |
| `backend/.env.example` | uygulama ayarları; compose bunu `env_file` ile yükler |

```bash
cp .env.example .env                  # POSTGRES_PASSWORD doldurulur
cp backend/.env.example backend/.env  # SECRET_KEY / EMAIL_PEPPER_KEY: openssl rand -hex 32
docker compose up -d --build
curl http://localhost:8000/health
```

Migration'lar konteyner açılışında koşar; elle: `docker compose run --rm --entrypoint alembic
api upgrade head`. Entrypoint DB'yi **beklemez**, compose'da `db` healthcheck'i örter.

- **Tek worker zorunlu.** Rate limiting in-memory (Redis yok); her worker kendi sayacını tutar,
  N worker limiti N katına çıkarır. `--scale api=N` yapılmamalı.
- **Host'ta `postgresql.service` 5432'yi tutuyorsa** compose `db` aynı anda kalkamaz; ikisi yan
  yana istenirse host portu `${DB_PORT:-5432}:5432` yapılır.
- `k-rs-_pgdata` volume'ü PG16 formatında eski bir katalog kopyası taşıyor. Compose yeniden
  kullanılacaksa `docker compose down -v` ile temiz açılır, migration'lar şemayı kurar.
- **Mail:** `RESEND_API_KEY` boşken gönderim yapılmaz, OTP konsola düşer — yerel akış çalışır.
- **Reverse proxy:** uvicorn düz HTTP servis eder. Önüne nginx/Caddy konursa
  `--proxy-headers --forwarded-allow-ips=<proxy-ip>` ve `TRUSTED_PROXY_IPS` gerekir; yoksa rate
  limit tüm istekleri proxy'nin IP'si sanar. ⚠️ Bu yalnızca nginx yolu içindir, Heroku'da
  `TRUSTED_PROXY_IPS` **set edilmez** (§6).

---

## 2. Prod deploy — adımlar

### 2.1 Uygulama ve veritabanı

```bash
cd /home/amnesia/Projects/K-rs-
heroku stack:set container --app kursu        # app zaten var, heroku-24'ten container'a alınır
heroku git:remote --app kursu                 # heroku remote'u ekler
heroku addons:create heroku-postgresql:essential-0 --app kursu   # DATABASE_URL'i kendi set eder
heroku pg:info --app kursu                # PG sürümünü not al (dev 18.4, Heroku 18.3)
```

### 2.2 Config vars

⚠️ `CF_ORIGIN_SECRET` **bu adımda verilmez**. Dolu olduğu an kilit devreye girer ve
`X-Origin-Secret` başlığı olmayan her istek 403 alır; Transform Rule henüz yokken bu "her
istek" demektir. §2.6'da açılır.

```bash
heroku config:set --app kursu \
  SECRET_KEY=$(openssl rand -hex 32) \
  EMAIL_PEPPER_KEY=$(openssl rand -hex 32) \
  RUN_MIGRATIONS=0 \
  DOCS_ENABLED=false \
  DB_POOL_SIZE=4 DB_MAX_OVERFLOW=8 DB_POOL_TIMEOUT=5 THREADPOOL_TOKENS=6 \
  UVICORN_LIMIT_CONCURRENCY=32 \
  ALLOWED_ORIGINS=https://kursu.live,https://www.kursu.live \
  HF_API_TOKEN=<hf token> \
  RESEND_API_KEY=<re_ ile başlayan anahtar> \
  MAIL_FROM='Kürsü <noreply@kursu.live>' \
  SENTRY_DSN=<dsn> SENTRY_ENVIRONMENT=production
```

Değerlerin gerekçesi §6'da. `MAIL_FROM`'un domain'i Resend'de SPF/DKIM ile doğrulanmış olmalı.

### 2.3 İlk deploy

```bash
git push heroku main
heroku ps:type web=basic --app kursu       # ilk deploy'dan ÖNCE çalışmaz: formation yok
heroku ps --app kursu                      # "web (Basic): ..." göründüğü doğrulanır
heroku logs --tail --app kursu
heroku releases:output --app kursu        # release phase'in alembic çıktısı
curl https://kursu-f792d82f3244.herokuapp.com/health
```

Build → release phase (`alembic upgrade head`, `heroku.yml`) → dyno. `RUN_MIGRATIONS=0` web
dyno'da tekrarı kapatır; tekrarlarsa bir migration hatası crash-loop'a döner.

⚠️ **İlk push kırılırsa bakılacak ilk yer `pg_trgm`.** Migration `ca37a91e7b75` extension'ı
kuruyor, Heroku eklentileri `heroku_ext` şemasına zorluyor. Migration bunu çalışma anında
yokluyor (şema varsa `WITH SCHEMA heroku_ext`) ama Heroku'ya karşı doğrulanmadı.

### 2.4 Katalog verisi ve admin

Şema boş gelir; katalog (219 üniversite / 2127 fakülte / 12273 bölüm + PAÜ ders/hoca)
snapshot'tan yüklenir. Migration'dan **sonra**, tablolar boşken:

```bash
cd backend
../.venv/bin/python seeds/load_snapshot.py \
  --database-url $(heroku config:get DATABASE_URL --app kursu) --dry-run
# özet doğruysa --dry-run kaldırılır
```

`pg_dump | heroku pg:psql` yerine bu tercih edilir: snapshot yalnızca katalog tablolarını taşır
(`users`, `email_verifications`, `reviews`, `reports` yok), alembic head'ini doğrular, kolonları
ada göre eşler ve sonda sequence'leri `max(id)+1`'e çeker. Dump yolunda sequence'ler dev DB'nin
değerinde kalır ve ilk insert'ler duplicate key yer.

⚠️ **Şema her değiştiğinde snapshot yeniden dökülmeli** (`seeds/dump_snapshot.py --force`),
yoksa `load_snapshot.py` head kontrolüne takılır ve prod'un ilk veri yüklemesi başarısız olur.
Snapshot dosyası `.gitignore`'da, temiz bir clone'da yok.

Admin kullanıcısı:

```bash
cd backend
env DATABASE_URL=$(heroku config:get DATABASE_URL --app kursu) \
    EMAIL_PEPPER_KEY=$(heroku config:get EMAIL_PEPPER_KEY --app kursu) \
    ../.venv/bin/python scripts/make_admin.py --department-id <id> --enrollment-year <yıl>
```

`make_admin.py` imajda yok (`.dockerignore`), bu yüzden `heroku run` değil host'tan koşar.

⚠️ **`EMAIL_PEPPER_KEY` mutlaka prod'unki olmalı.** Yalnızca `DATABASE_URL` geçirilirse script
pepper'ı `backend/.env`'den, yani dev'den okur; `email_hash` = HMAC(pepper, e-posta) olduğu için
prod kendi pepper'ıyla hesapladığında satırı bulamaz. Sonuç: doğru şifreyle bile "e-posta veya
şifre hatalı", "şifremi unuttum" da sessizce hiçbir mail göndermez (kullanıcı sayımına karşı
her durumda "gönderildi" der). `--department-id`/`--enrollment-year` verilmezse script'teki
varsayılanlar yazılır, prod'da doğru olmaları tesadüfe kalır.

### 2.5 api.kursu.live

```bash
heroku domains:add api.kursu.live --app kursu   # verdiği DNS target'ı yazar
heroku certs:auto:enable --app kursu            # ACM, Basic dyno'da ücretsiz
heroku domains --app kursu                      # "Cert issued" olana kadar izlenir
```

Cloudflare DNS'e o target'a `api` adıyla CNAME eklenir — **gri bulut** (proxy kapalı), proxy
açıkken ACM doğrulaması takılıyor. Sertifika çıkınca kayıt turuncuya çevrilir, SSL/TLS modu
**Full (strict)**.

Zone'da `*.kursu.live` wildcard A kaydı var (park IP'si); `api.kursu.live` eklenmeden önce de
çözülüyordu, "kayıt zaten var" sanılmasın. Spesifik CNAME wildcard'ı ezer, `*` kaydına
dokunulmaz. `kursu.live` ve `www` de aynı park IP'sinde — onların yeri §2.7'de Pages'e geçer.

### 2.6 Origin kilidi

`*.herokuapp.com` kapatılamıyor (Cedar'da IP allowlist yok) ve Cloudflare'i atlıyor; güven
çapası bu yüzden peer IP'de değil gizli başlıkta. Trafik artık CF'den geçtiğine göre:

1. `openssl rand -hex 32` ile bir sır üret.
2. Cloudflare → `kursu.live` → Rules → Transform Rules → Modify Request Header → statik
   `X-Origin-Secret` = o değer, kural `api.kursu.live` hostname'ine uygulanır.
3. `heroku config:set CF_ORIGIN_SECRET=<değer> --app kursu`

Sıra budur; tersi olursa aradaki sürede API tamamen 403 verir.

```bash
curl -i https://api.kursu.live/universities             # 200
curl -i https://kursu-f792d82f3244.herokuapp.com/universities    # 403
```

`/health` kilitten muaf (`main.py`), Heroku'nun kendi kontrolü için.

### 2.7 Frontend — Cloudflare Pages

Cloudflare → Workers & Pages → Create → Pages → GitHub repo'su:

| Ayar | Değer |
|---|---|
| Kök dizin | `frontend` |
| Build komutu | `npm run build` |
| Çıktı dizini | `dist` |
| Env değişkeni | `VITE_API_URL=https://api.kursu.live` |

`VITE_API_URL` build anında bundle'a gömülür, sonradan değiştirilirse yeniden build gerekir —
adım bu yüzden §2.5'ten sonra. Boş bırakılırsa `axios.js` `/api`'ye düşer; Pages'te o yolu
taşıyacak bir proxy katmanı yok, tam adres şart.

Build bitince Custom domains → `kursu.live` ve `www.kursu.live`; Pages DNS kayıtlarını kendi
kurar. SPA fallback için `frontend/public/_redirects` repoda (`/* /index.html 200`) — onsuz
`BrowserRouter` yollarında sayfa yenilendiğinde 404 gelir.

---

## 3. Doğrulama

- Release phase migration'ı gerçekten koştu mu: `heroku releases:output` çıktısında alembic
  logu. ENTRYPOINT argümanı yutulsaydı adım başarılı görünüp hiçbir şey yapmazdı.
- Origin kilidi devrede mi: §2.6'daki iki `curl` (200 / 403).
- Uçtan uca kayıt: gerçek e-posta → OTP maili → doğrulama → giriş.
- Yorum yaz → `pending` → HF moderasyonu sonucu değiştiriyor mu.
- Admin paneline giriş.
- İlk yedek: `heroku pg:backups:capture --app kursu` (Essential'da otomatik rollback yok).

Heroku belgelerinden alınan, koda karşı doğrulanamayan varsayımlar: `USER kursu` (uid 1000) ile
konteyner çalıştırma kuralının uyumu, ACM'in gri bulut gereksinimi, Essential-0'ın 20 bağlantı /
1 GB rakamları.

---

## 4. Deploy'u bloke etmeyen Cloudflare kuralları

Kampüs NAT'ı probleminin kenar tarafındaki çözümü; site ayağa kalktıktan sonra eklenir.

**Rate Limiting Rule → Managed Challenge** (`/auth/*`, arama uçları). Aynı IP arkasında botu
insandan ayıran tek ücretsiz sinyal CF'nin bot tespiti. Meşru kullanıcı challenge'ı sessizce
geçer, script geçemez; ayrım IP'de olmadığı için NAT sorun olmaktan çıkar. Kullanıcıya bulmaca
gösteren CAPTCHA reddedildi, Managed Challenge bulmaca göstermez.

**Cache Rule → public okuma uçları, TTL 30-60 sn.** ⏸️ Ertelendi: ölçüm okuma uçlarında
0.5 CPU'da 66–140 rps buldu, kapasite gerekçesi düştü. Karşı taraftaki risk durmaya devam
ediyor — `Authorization` başlıklı istek önbelleğe **girmemeli** (aynı uçlar admin'e pending
yorumları döner) ve free plan'da auth'a göre cache key ücretli, kalan yol elle path kuralı.
Eklenirse query string allowlist'i (`page`, `size`, `q`, `sort`) şart, yoksa `?x=1` ile
atlanır.

---

## 5. Operasyon

```bash
heroku pg:backups:capture --app kursu     # Essential'da rollback/follower yok, manuel
heroku pg:backups:download --app kursu
heroku logs --tail --app kursu
```

**Kapasite (2026-08-04 ölçümü, 0.5 CPU / 512 MB):** okuma uçları 66–140 rps, 1.0 CPU'da ölçek
neredeyse doğrusal (2.06×). Tavanı CPU belirliyor, RAM değil — yük altında bellek 78 MB'de
kaldı, CPU kotanın tamamına yapıştı. En pahalı tek iş bcrypt. 44 bin review + index'lerle DB
38 MB, Essential-0'ın 1 GB'ına uzak.

**Olay anında tepki:** limitler env'de, rebuild'siz daraltılır; CF'de tek IP/ASN elle
bloklanabilir (kill switch). Uygulama katmanında, NAT arkasındaki ucuz ve **başarılı** istekleri
meşru kullanıcıdan ayırmanın ücretsiz yolu yok — kalan artık, challenge'ı geçen headless
tarayıcı. Bu ölçekte kabul edildi.

---

## 6. Config var referansı

Prod'da set edilenler ve gerekçeleri (varsayılanlar `backend/app/core/config.py`):

| Değişken | Prod değeri | Neden |
|---|---|---|
| `SECRET_KEY` | rastgele 32 bayt | JWT imzası |
| `EMAIL_PEPPER_KEY` | rastgele 32 bayt | `email_hash` HMAC'ı. `SECRET_KEY`'den **farklı** olmalı ve **asla rotate edilmez** — değişirse tüm kullanıcılar giriş yapamaz |
| `RUN_MIGRATIONS` | `0` | Release phase zaten koşuyor; web dyno'da tekrarı crash-loop riski |
| `DOCS_ENABLED` | `false` | Varsayılan `true`; açık kalırsa `/docs`, `/redoc`, `/openapi.json` admin imzaları dahil kimliksiz listelenir |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT` | `4` / `8` / `5` | Essential-0'ın toplam 20 bağlantısı var, pgbouncer yok |
| `THREADPOOL_TOKENS` | `6` | Sync uçlar anyio threadpool'unda koşar, her handler tepede 2 bağlantı tutabilir: 2 × token ≤ pool + overflow |
| `UVICORN_LIMIT_CONCURRENCY` | `32` | Uçuştaki istek tavanı. Tavansız kalınca aşırı yükte havuz tükeniyor ve istekler 503 yerine 500 alıyor |
| `ALLOWED_ORIGINS` | Pages domainleri | Virgülle ayrılmış düz string, JSON dizisi değil |
| `HF_API_TOKEN` | HF token'ı | Boşsa istek kırılmaz ama **her** yorum `pending`'de kalır |
| `RESEND_API_KEY` | `re_…` | Boşsa mail gitmez (`mail.failed` artar), kimse kayıt olamaz |
| `MAIL_FROM` | `Kürsü <noreply@kursu.live>` | Domain Resend'de doğrulanmış olmalı |
| `SENTRY_DSN` / `SENTRY_ENVIRONMENT` | dsn / `production` | Boş DSN = Sentry hiç başlatılmaz |
| `CF_ORIGIN_SECRET` | Transform Rule'daki değer | **En son** set edilir (§2.6) |

Prod'da **set edilmeyenler**:

- `MAIL_DEV_CONSOLE` — `true` olursa OTP'ler `heroku logs`'a düşer, logu okuyan hesap devralır.
- `TRUSTED_PROXY_IPS` — Heroku'da `request.client.host` her zaman router'ın dokümante edilmeyen
  iç adresi; `client_ip()` CF yolunda `cf-connecting-ip`'yi gizli başlığa güvenerek okur.
  Set edilirse yanlış çapaya güvenilmiş olur. (Kendi sunucuna/nginx'e dönülürse tam tersi:
  ayarlanmadan proxy arkasına geçilmemeli, yoksa limitler tek global kovaya çöker.)

⚠️ Kilit açılana kadar (§2.3–§2.6 arası) rate limit anahtarı Heroku router'ının IP'sine düşer,
yani tüm trafik tek kovada olur. O pencereyi uzatma; başka etkisi yok.

---

## 7. Bilinen riskler

**Mail M365 kutusunda sessizce kaybolabilir.** 2026-08-05 provasında `@posta.pau.edu.tr`
adresine giden ilk mail hiçbir klasörde bulunamadı (inbox, Junk, Other, karantina boş), sonraki
testler doğrudan inbox'a düştü ve neden bulunamadı. Elenen adaylar, tekrar denenmesin diye:
DMARC eksikliği (kayıt en baştan vardı), safe senders (eklenip çıkarıldı, ikisinde de geldi),
domain warmup (bu hacimde oluşmaz), tenant allow-list (kimseyle görüşülmedi). Gönderici tarafta
eksik yok: harici Gmail'e SPF/DKIM/DMARC üçü de PASS.

⚠️ Resend'deki `delivered` ve SMTP'nin `250 Queued mail for delivery` yanıtı **teşhis için
kullanılamaz** — ikisi de yalnızca M365'in mesajı kabul ettiğini söyler, hangi klasöre koyduğunu
değil. Erken uyarının gerçek göstergesi mail domaini başına "OTP gönderildi / OTP doğrulandı"
oranı; çok üniversiteye açılırken `services/metrics.py`'ye eklenir, MVP'de gerekmez.

**Moderasyon timeout'u 20 sn.** Ücretsiz HF katmanında model boşta kalınca uykuya geçiyor ve ilk
yorum `httpx.ReadTimeout` ile `pending`'de kalıyordu. Task arka planda koştuğu için kullanıcı
beklemez, ama threadpool token'ını 20 sn'ye kadar tutabilir — `THREADPOOL_TOKENS=6` ile aynı
anda 6 soğuk moderasyon diğer sync uçları bekletir. Yük altında ilk bakılacak yer burası.

**Dyno günde en az bir kez restart olur** ve dosya sistemi ephemeral; in-memory rate limit
sayaçları sıfırlanır. Kabul ediliyor, ağır işi kenar yapıyor (§4).

**`requirements.txt`'te `starlette` ve `anyio` doğrudan bağımlılık olmadıkları hâlde pinli:**
`core/limiter.py:NestedRouteSlowAPIMiddleware` FastAPI/Starlette iç yapısına, `main.py` lifespan'i
`anyio.to_thread.current_default_thread_limiter()` iç API'sine dayanıyor. Sessizce sürüm
atlarlarsa ilk kırılacak yerler orası.
