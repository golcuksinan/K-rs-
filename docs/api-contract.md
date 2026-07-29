# Kürsü API Sözleşmesi

Bu doküman **OpenAPI'nin ifade edemediği** kuralları anlatır: zarflar, akışlar, maskeleme,
hata gövdeleri, kısıtlar. Alan alan şema listesi burada **yoktur** — makine okunur sözleşme
için `docs/openapi.json` veya canlı `/docs` kullanılır.

`openapi.json` elle düzenlenmez, bayatlar. Endpoint imzası değişince `backend/` içinden
yeniden üretilir:

```bash
cd backend
../.venv/bin/python -c "import json, pathlib; from main import app; pathlib.Path('../docs/openapi.json').write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding='utf-8')"
```

> Komut **`backend/` içinden** çalıştırılmalı: `main` importu `.env`'i relative yoldan okur
> (`DATABASE_URL`, `SECRET_KEY`, `EMAIL_PEPPER_KEY`), başka dizinden "Field required" verir.

---

## 1. Genel

- Base URL: dev'de `http://127.0.0.1:8000`. Prefix yok — router path'leri kökten başlar.
- `GET /health` → `{"status": "ok"}`, **rate limit muaf**.
- Swagger: `/docs` — token elle girilir (HTTPBearer, otomatik login formu yok).
- CORS: izinli origin'ler `ALLOWED_ORIGINS` env'inden gelir (virgülle ayrılmış, varsayılan `"*"`).
  **`allow_credentials=False`** → cookie/session yok; token'ı frontend kendisi saklar ve taşır.

## 2. Auth akışı

| Uç | Gövde döner |
|---|---|
| `POST /auth/register` | `{message}` — OTP e-postaya gider, kullanıcı **henüz oluşmaz** |
| `POST /auth/verify-otp` | `{access_token, token_type: "bearer"}` — **kullanıcı burada oluşur** |
| `POST /auth/login` | aynı token gövdesi |
| `POST /auth/forgot-password` | `{message}` — adres kayıtlı olmasa da **aynı** mesaj (enumeration koruması) |
| `POST /auth/reset-password` | `{message}` |

- Token: `Authorization: Bearer <token>`. Ömür **60 dk** (`ACCESS_TOKEN_EXPIRE_MINUTES`).
  **Refresh token yok** → 401 alınca yeniden login.
- **Şifre değiştirme ucu yok** (bilinçli): akış forgot-password + reset-password (OTP) üzerinden.
- Kısıtlar: e-posta **sadece `@posta.pau.edu.tr`**; şifre min 8 karakter + **en az 1 rakam**
  (register ve reset'te; **login'de doğrulanmaz**); OTP 6 hane, **10 dk** geçerli
  (`OTP_EXPIRE_MINUTES`), **5 yanlış deneme** sonrası kayıt silinir → baştan başlanır.
- ⚠️ `verify-otp`'ye forgot-password kodu verilirse **400**:
  "Bu kod şifre sıfırlama için üretilmiş, kayıt için kullanılamaz". Kod **silinmez**, aynı kodla
  reset akışı devam edebilir.
- ⚠️ **`email_service.py` şu an `print()` stub** — mail gerçekten gönderilmiyor. Lokalde OTP
  **backend konsolundan** okunur. Bunu bilmeyen frontend geliştiricisi kayıt akışını test edemez.

## 3. Liste sözleşmesi — `Page[T]`

JSON dizisi dönen **her top-level uç** şu zarfı döner:

```json
{ "items": [...], "total": 123, "limit": 50, "offset": 0 }
```

- `limit`: 1..100, varsayılan **50**. `offset`: ≥ 0. Aralık dışı değer → 422.
- **İstisna yok.** Buna karşılık detay yanıtlarının **içindeki** koleksiyonlar
  (`CourseProfessorDetail.reviews`, `ProfessorDetail.courses`) düz dizidir, sayfalanmaz.
- ⚠️ `GET /departments` gruplama dalında `total` = **grup sayısı**, eşleşen bölüm satırı değil.

## 4. Endpoint tablosu

Yetki üç değerden biri: `public` · `auth` (Bearer zorunlu) · `admin` (rol=admin).

| Grup | public | auth | admin |
|---|---|---|---|
| `auth` | 5 ucun hepsi | — | — |
| `universities` / `faculties` / `departments` / `courses` | `GET` (liste) | — | `POST`, `PATCH /{id}`, `DELETE /{id}` (soft-delete) |
| `professors` | `GET` (liste), `GET /{id}`* | — | — |
| `course-professors` | `GET` (liste), `GET /{id}`* | — | — |
| `reviews` | `GET /reviews` | `POST`, `GET /me`, `PATCH /{id}`, `DELETE /{id}` | `GET /pending`, `PATCH /{id}/status` |
| `reports` | — | `POST`, `GET /me` | `GET /pending`, `PATCH /{id}/status` |
| `users` | — | `GET /me` | — |
| — | `GET /health` | — | — |

\* **Opsiyonel auth:** token varsa ve admin ise tüm review'lar görünür; token yoksa/geçersizse
hata fırlatılmaz, sadece `approved` olanlar döner.

Zorunlu filtre kuralları:

- `GET /faculties` → `university_id` **zorunlu** (yoksa 422).
- `GET /courses` → `department_id` yoksa `search` zorunlu, **en az 2 karakter**, aksi halde 422.
- `GET /departments` → `faculty_id` yoksa `search` zorunlu (**boş olmaması yeterli, uzunluk
  kontrolü yok**), aksi halde 422.
- `GET /course-professors` → `course_id` **zorunlu**; `term` verilmezse **en güncel dönem**
  otomatik seçilir.

Arama davranışı: `search` `GET /faculties`/`GET /departments`/`GET /professors`'ta **ad** üzerinde;
`GET /courses` ad **ve ders kodunda**, `GET /universities` ad **ve kısaltmada** (`short_name`) arar.

Silme hep **soft-delete**'tir (`deleted_at`), kayıt fiziksel olarak durur. Tek istisna
`DELETE /reviews/{id}` — o gerçekten siler (aşağı bkz.).

## 5. Review yaşam döngüsü — frontend'in en çok yanılacağı yer

1. `POST /reviews` → **201**, gövdede `status: "pending"`. **AI moderasyonu beklenmez**,
   arka planda çalışır.
2. Sonuç `approved` / `rejected` / `pending` olur. Ortadaki belirsizlik bandı (0.35–0.70)
   `pending`'de bırakır → insan (admin) onayı bekler.
3. **Push/WebSocket yok** — frontend polling yapar: `GET /reviews/me`
   (`created_at` **azalan** → yeni review `items[0]`), dönen `id` ile eşleştirilir.
4. Aynı `course_professor_id`'ye ikinci review → **400** "Bu derse zaten bir değerlendirme
   yaptınız". Geçersiz `course_professor_id` → 404.
5. `POST /reviews` skorları (`teaching`/`difficulty`/`fairness`) **1..5**, `comment` opsiyonel,
   en fazla 2000 karakter.

**Düzenleme akışı:**

- `status == "approved"` bir review `PATCH` edilirse **public hali değişmez**: yeni değerler
  `pending_*` alanlarına yazılır, `has_pending_edit: true` olur, admin onayı bekler.
  Frontend `has_pending_edit` true iken "değişiklik onay bekliyor" göstermeli.
- `pending` / `rejected` olanlar **doğrudan** güncellenir ve tekrar `pending`'e döner.
- Admin `PATCH /reviews/{id}/status` (`approved` | `rejected`): `has_pending_edit` true ise bunu
  **edit onayı/reddi** olarak işler — approve'da gölge alanlar asıla kopyalanır, reject'te sadece
  temizlenir; **her iki durumda da `status`'a dokunulmaz** (review `approved` kalır).
- `pending_*` ve `has_pending_edit` alanları sadece `GET /reviews/me` ve `GET /reviews/pending`
  yanıtlarında (`ReviewFullResponse`) döner; public `GET /reviews`'ta yoktur.

⚠️ `DELETE /reviews/{id}` (204) o review'a ait **Report satırlarını da siler**.

**Report tarafı:** `POST /reports` (`review_id` + `reason`, 3..500 karakter). Aynı review'a ikinci
report → **400**. Admin `PATCH /reports/{id}/status` değerleri **`resolved` | `dismissed`**
(review'unkilerden farklı). Yanıtlarda `reporter_id` bilinçli olarak **dönmez**.

**Anonimlik:** hiçbir yanıtta `user_id` / `email` / review↔kullanıcı eşleşmesi dönmez.

## 6. Maskeleme kuralları

Üst kayıt soft-delete edilmişse alt kayıtlar listelenmeye devam eder, sadece **adı** maskelenir
(`core/masking.py`): `"Silinmiş Üniversite"` / `"Silinmiş Fakülte"` / `"Silinmiş Bölüm"` /
`"Silinmiş Ders"`.

- Sadece **isim** maskelenir — `*_id` ve `course_code` her zaman gerçek değerdir.
- İsim olmayan alan (`university_short_name`) placeholder almaz; üst kayıt silinmişse **`null`**.
- Geçerli olduğu yerler: `GET /departments` (gruplama dalı), `GET /courses`,
  `GET /course-professors/{id}`, `GET /professors/{id}`, `GET /users/me`.
- **Bilinçli istisna:** düz liste dalları (`?faculty_id=` gibi filtreli çağrılar) maskelemeye
  dahil değildir.

## 7. Hata gövdesi şekilleri — **üç farklı şekil var**

Frontend tek bir `parseError(response)` yardımcısı yazmalı:

| Durum | Gövde | Not |
|---|---|---|
| 4xx (`HTTPException`) | `{"detail": "Türkçe mesaj"}` | string |
| 422 (validation) | `{"detail": [{"loc": …, "msg": …, "type": …}]}` | **dizi** — doğrudan basılırsa `[object Object]` |
| 429 (rate limit) | `{"error": "Rate limit exceeded: 5 per 1 minute"}` | anahtar **`detail` değil `error`** (slowapi'nin kendi handler'ı) |

Not: 422 elle de fırlatılabiliyor (`GET /departments`, `GET /courses` zorunlu filtre kuralları) —
o durumda `detail` **string**'tir. Yani 422 gövdesi iki şekilden biri olabilir; tip kontrolü şart.

## 8. Rate limitler

- Global **`100/minute`** (IP başına).
- 5 auth ucunun her biri ayrıca **`5/minute`**.
- `GET /health` **muaf**.
- In-memory (Redis yok) → multi-worker'da limit worker sayısı kadar katlanır; süreç yeniden
  başlayınca sayaç sıfırlanır.

## 9. Bilinen kısıtlar (frontend tasarımını etkiler)

- ⚠️ Postgres `ILIKE` Türkçe **`İ/ı` eşleşmesi yapmaz** — `"bilgisayar"` araması `"BİLGİSAYAR"`
  bulmaz. Arama kutusu bu varsayımla tasarlanmalı.
- `GET /departments` **iki farklı şekil** döner: `faculty_id` verilirse düz bölüm listesi,
  verilmezse isim bazlı **gruplanmış** liste (`{department_name, faculties[]}`).
- Gruplama dalında ham sorguya **500 satırlık** tavan var (`GROUP_SEARCH_ROW_CAP`); çok geniş
  aramalarda sonuç kırpılır.
- Farklı yazılmış ama anlamca aynı bölüm isimleri **ayrı grup** kalır (normalize edilmiyor).
- **Mevcut veri:** 220 üniversite / 2130 fakülte / 12297 bölüm. Ders + hoca verisi **yalnızca
  PAÜ** için var (139 lisans programı; 16.253 ders, 1.650 hoca, 37.165 ders-hoca eşleşmesi) —
  diğer üniversitelerin bölümlerinde ders listesi **boş** gelir. Ayrıca PAÜ derslerinin
  **5.322'sinde hiç hoca yok** (EBS'de o dersin şubesi açılmamış), yani dolu bir bölümde bile
  boş ders detayı görülebilir → boş durum (empty state) tasarımı şart.
- Üniversitelerin `city` alanı gerçek veri değil, hepsi `"Bilinmiyor"`.
- Ortalamalar **her zaman** yalnızca `approved` review'lardan hesaplanır (admin görüntülemesinde
  bile); review **listesi** admin'e hepsini gösterir.

## 10. ⚠️ Düzeltilmesi Gerekenler

Bu iş kapsamında **düzeltilmedi**, kayda geçirildi (kullanıcı kararı). Frontend mevcut davranışa
göre yazar; düzeltmeler ayrı iş olarak sıraya girer.

1. **`GET /reviews/{id}` yok.** Moderasyon polling'i `GET /reviews/me`'nin tüm sayfasını çekmek
   zorunda. → Sahip-veya-admin yetkili tekil uç eklenmeli.
2. **429 gövdesi `{"error": …}`**, diğer tüm hatalar `{"detail": …}` → iki ayrı parse yolu
   gerekiyor. → `RateLimitExceeded` için özel handler yazılıp `detail`'e çevrilmeli.
3. **422'de `detail` bazen dizi bazen string.** → Kalıcı çözüm ortak hata zarfı.
4. **`GET /departments` union döner** → OpenAPI'de `anyOf`, tip üretimini (codegen) zorlaştırıyor.
   → Gruplama ayrı uca alınabilir (`/departments/grouped`).
5. **`email_service.py` `print()` stub** — lokalde OTP konsoldan okunuyor. → Gerçek SMTP (DevOps).

`info.version` = **`0.1.0`** artık bilinçli: 0.x, "sözleşme kırılabilir" demek ve yukarıdaki
maddeler kapandıkça kırılacak. İlk kararlı sürümde 1.0.0'a çıkar.
