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
| `POST /auth/register` | `{message}` — OTP e-postaya gider, kullanıcı **henüz oluşmaz**. Adres zaten kayıtlıysa da **aynı** mesaj döner (enumeration koruması) — durum adres sahibine mail ile bildirilir, OTP üretilmez |
| `POST /auth/verify-otp` | `{access_token, token_type: "bearer"}` — **kullanıcı burada oluşur** |
| `POST /auth/login` | aynı token gövdesi |
| `POST /auth/forgot-password` | `{message}` — adres kayıtlı olmasa da **aynı** mesaj (enumeration koruması) |
| `POST /auth/reset-password` | `{message}` |

- Token: `Authorization: Bearer <token>`. Ömür **60 dk** (`ACCESS_TOKEN_EXPIRE_MINUTES`).
  **Refresh token yok** → 401 alınca yeniden login.
- ⚠️ **`reset-password` o kullanıcının önceki tüm token'larını geçersiz kılar** — sıfırlamadan
  önce alınmış token'la yapılan her istek **401** döner. Frontend başka bir sekmede/cihazda
  açık oturumu bu 401'de login'e düşürmeli.
- **Şifre değiştirme ucu yok** (bilinçli): akış forgot-password + reset-password (OTP) üzerinden.
- Kısıtlar: e-posta **sadece `@posta.pau.edu.tr`** ve `department_id` o domain'in üniversitesine
  (Pamukkale) ait olmak zorunda — çapraz seçim **400** "Bu e-posta adresiyle yalnızca … bölümlerine
  kayıt olunabilir" (harita: `core/security.py` `EMAIL_DOMAIN_UNIVERSITIES`); şifre min 8 karakter + **en az 1 rakam**
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
- **İstisna yok.** Buna karşılık detay yanıtlarının **içindeki** koleksiyon
  (`ProfessorDetail.courses`) düz dizidir, sayfalanmaz — hoca başına ders sayısı sınırlıdır.
- ⚠️ `GET /departments` gruplama dalında `total` = **grup sayısı**, eşleşen bölüm satırı değil.

## 4. Endpoint tablosu

Yetki üç değerden biri: `public` · `auth` (Bearer zorunlu) · `admin` (rol=admin).

| Grup | public | auth | admin |
|---|---|---|---|
| `auth` | 5 ucun hepsi | — | — |
| `universities` / `faculties` / `departments` / `courses` | `GET` (liste) | — | `POST`, `PATCH /{id}`, `DELETE /{id}` (soft-delete) |
| `professors` | `GET` (liste), `GET /{id}` | — | — |
| `course-professors` | `GET` (liste), `GET /{id}` | — | `POST` |
| `reviews` | `GET /reviews` | `POST`, `GET /me`, `PATCH /{id}`, `DELETE /{id}` | `GET /reviews?status=`, `GET /pending`, `PATCH /{id}/status`, `PATCH /{id}/edit-status` |
| `reports` | — | `POST`, `GET /me` | `GET /pending`, `PATCH /{id}/status` |
| `users` | — | `GET /me` | — |
| `admin/stats` | — | — | `GET /admin/stats`, `GET /admin/stats/events` |
| — | `GET /health` | — | — |

Zorunlu filtre kuralları:

- `GET /faculties` → `university_id` **zorunlu** (yoksa 422).
- `GET /courses` → `department_id` yoksa `search` zorunlu, **en az 2 karakter**, aksi halde 422.
  Verilen `department_id` hiç yoksa **404** (soft-delete edilmiş bölüm 404 değil, aşağı bkz. §6).
- `GET /departments` → `faculty_id` yoksa `search` zorunlu (**boş olmaması yeterli, uzunluk
  kontrolü yok**), aksi halde 422.
- `GET /course-professors` → `course_id` **zorunlu**; `term` verilmezse **en güncel dönem**
  otomatik seçilir.
- `POST /course-professors` (admin) → `{course_id, professor_id, term}`. Aynı üçlü ikinci kez →
  **400** (DB'de `uq_course_professor_term` unique constraint'i var).

Arama davranışı: `search` `GET /faculties`/`GET /departments`/`GET /professors`'ta **ad** üzerinde;
`GET /courses` ad **ve ders kodunda**, `GET /universities` ad **ve kısaltmada** (`short_name`) arar.
`%` ve `_` joker değil **literal karakter** olarak eşleşir.

⚠️ **`PATCH /faculties/{id}` ve `PATCH /departments/{id}` yalnızca `name` alır.** Üst kayıt
alanları (`university_id` / `faculty_id`) gövdede gönderilse de **yok sayılır** (200 döner, kayıt
değişmez): taşıma dersin kanonik kimliğini (`university_id` + kod + ad) kırardı. Taşıma ucu yok.

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
   yaptınız". Geçersiz `course_professor_id` → 404. Eşleşme dursa da **dersi soft-delete
   edilmişse → 400** "Geçersiz course_id" (silinmiş derse yeni yorum yazılamaz; eski onaylı
   yorumlar görünmeye devam eder).
5. `POST /reviews` skorları (`teaching`/`difficulty`/`fairness`) **1..5**, `comment` opsiyonel,
   en fazla 2000 karakter.

**Düzenleme akışı:**

- `status == "approved"` bir review `PATCH` edilirse **public hali değişmez**: yeni değerler
  `pending_*` alanlarına yazılır, `has_pending_edit: true` olur, admin onayı bekler.
  Frontend `has_pending_edit` true iken "değişiklik onay bekliyor" göstermeli.
- `pending` / `rejected` olanlar **doğrudan** güncellenir, tekrar `pending`'e döner ve AI
  moderasyonu **yeniden tetiklenir** (create ile aynı döngü — polling yine gerekir).
- Admin tarafında iki ayrı uç (ikisi de `{"status": "approved" | "rejected"}` alır):
  - `PATCH /reviews/{id}/status` — review'un **kendisinin** onayı/reddi. Reject, bekleyen edit
    olsa bile review'u komple yayından kaldırır (gölge alanlar da temizlenir).
  - `PATCH /reviews/{id}/edit-status` — **bekleyen edit'in** onayı/reddi; `has_pending_edit`
    false ise **400**. Approve gölge alanları asıla kopyalar, reject sadece temizler;
    iki durumda da `status`'a dokunulmaz (review `approved` kalır).
- `pending_*` ve `has_pending_edit` alanları sadece `GET /reviews/me` ve `GET /reviews/pending`
  yanıtlarında (`ReviewFullResponse`) döner; public `GET /reviews`'ta yoktur.

**Yorum okumanın tek yolu `GET /reviews`'tur.** Detay uçları (`GET /course-professors/{id}`,
`GET /professors/{id}`) yorum listesi **döndürmez**, yalnızca ortalamaları ve `review_count`'u
verir — yanıt boyutu yorum sayısından bağımsızdır. Bir ders/hoca sayfası iki istek yapar:

- `?course_professor_id=` — tek ders-hoca eşleşmesinin yorumları.
- `?professor_id=` — hocanın **tüm derslerindeki** yorumları, tek listede.
- İkisi de verilirse ikisi birden uygulanır (AND).

Varsayılan olarak yalnızca `approved` döner. `?status=approved|pending|rejected` **admin
token'ı ister**: eksik/yetkisiz token ile **403**, tanımsız değer **422**. Bu, `rejected`
yorumları listeleyebilen tek yoldur (`GET /reviews/pending` yalnızca `pending` + bekleyen
edit'leri verir).

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
- ⚠️ **"Hiç yok" ile "silinmiş" farklı sonuç verir:** `GET /courses?department_id=` var olmayan
  bölüm için **404**, soft-delete edilmiş bölüm için **200** + `"Silinmiş Bölüm"` döner.
- Sayaçlar silinmiş kayıtları saymaz: `department_count` yalnızca **aktif** bölümleri,
  `GET /professors`'taki `course_count` yalnızca **aktif** dersleri sayar.

## 7. Hata gövdesi şekilleri — **üç farklı şekil var**

Frontend tek bir `parseError(response)` yardımcısı yazmalı:

| Durum | Gövde | Not |
|---|---|---|
| 4xx (`HTTPException`) | `{"detail": "Türkçe mesaj"}` | string |
| 422 (validation) | `{"detail": [{"loc": …, "msg": …, "type": …}]}` | **dizi** — doğrudan basılırsa `[object Object]` |
| 429 (rate limit) | `{"error": "Rate limit exceeded: 20 per 1 minute"}` | anahtar **`detail` değil `error`** (slowapi'nin kendi handler'ı) |

Not: 422 elle de fırlatılabiliyor (`GET /departments`, `GET /courses` zorunlu filtre kuralları) —
o durumda `detail` **string**'tir. Yani 422 gövdesi iki şekilden biri olabilir; tip kontrolü şart.

## 8. Rate limitler

Değerler `.env`'den gelir (`RATE_LIMIT_*`), aşağıdakiler varsayılanlardır. **Kovalar uç
başınadır**: bir uçta 429 almak diğerlerini etkilemez.

- Global **`20/second` + `600/minute`** (ikisi birden). ⚠️ Saniyelik pencere aynı zamanda
  **paralel istek sayısına tavandır**: aynı anda 20'den fazla çağrı açan bir ekran fazlasından
  429 alır. React StrictMode dev'de effect'leri iki kez tetiklediği için bu sayı beklenenin
  iki katı olabilir.
- **Kova anahtarı:** `Authorization` başlığında geçerli bir token varsa **kullanıcı başına**,
  yoksa IP başına. Yani giriş yapmış kullanıcı NAT'ın arkasındaki kalabalıkla kova paylaşmaz.
  Geçersiz/süresi dolmuş token IP kovasına düşer.
- 5 auth ucunun her biri ayrıca **`20/minute`**, ve bunlar **her zaman IP başına** anahtarlanır
  (kimlik doğrulayan ucu kimlikle limitlemek anlamsız olurdu). ⚠️ Global limitler bunların
  **yerine geçmez, üstüne eklenir** — auth uçlarında saniyelik pencere de geçerlidir.
- `POST /auth/login` ayrıca **başarısız denemeleri** sayar: IP başına `10/minute`, hedef
  e-posta başına `5/minute`. Başarılı giriş bu kovaları tüketmez. Tavana çarpınca doğru şifre
  de 429 alır. Gövde hangi eksene takıldığını söylemez.
- `GET /health` **muaf**.
- In-memory (Redis yok) → multi-worker'da limit worker sayısı kadar katlanır; süreç yeniden
  başlayınca sayaç sıfırlanır.

## 9. Bilinen kısıtlar (frontend tasarımını etkiler)

- Arama **Türkçe harf katlamasından** geçer: `İ/I/ı/i`, `ş/s`, `ğ/g`, `ü/u`, `ö/o`, `ç/c` ayrımı
  yoktur — `"adıyaman"`, `"ADIYAMAN"` ve `"adiyaman"` aynı sonucu verir.
- `GET /departments` **iki farklı şekil** döner: `faculty_id` verilirse düz bölüm listesi,
  verilmezse isim bazlı **gruplanmış** liste (`{department_name, faculties[]}`).
- Farklı yazılmış ama anlamca aynı bölüm isimleri **ayrı grup** kalır (normalize edilmiyor).
- **Mevcut veri:** 219 üniversite / 2127 fakülte / 12273 bölüm. Ders + hoca verisi **yalnızca
  PAÜ** için var (139 lisans programı; 7.414 ders, 16.627 ders-bölüm bağı, 1.650 hoca,
  25.135 ders-hoca eşleşmesi) — diğer üniversitelerin bölümlerinde ders listesi **boş** gelir.
- ⚠️ **PAÜ derslerinin 1.625'inde (%22) hiç hoca yok** — EBS'de o dersin şubesi hiç açılmamış.
  Dolu bir bölümde bile boş ders detayı görülebilir. `GET /courses` her ders için
  **`professor_count`** döner (tekil hoca sayısı; aynı hocanın farklı dönemleri tek sayılır).
  `0` olan ders açıldığında **hiçbir şey yoktur** — ne hoca ne yorum, yorum da yazılamaz.
  Boş durum (empty state) tasarımı şart; sıralama/soluklaştırma bu alanla yapılır. Uç bunları
  **gizlemez**, kararı frontend verir. Hocasızların %91'i seçmeli (1.486 / 139) — aşağıdaki
  `is_elective` ile ayırt edilir.
- **Ders kanoniktir:** aynı ders birden çok bölümün müfredatında olsa da **tek kayıttır**
  (üniversite düzeyinde, `(kod, ad)` kimliğiyle) ve **tek yorum havuzu** taşır. Kaç bölümün
  müfredatında olduğu `department_count` alanında döner.
- **`?department_id=` dalı** dersin o bölümdeki kaydını döner: `department_*`, `faculty_*`,
  `semesters`, `is_elective` dolu. **`search` dalında** (bölüm verilmeden) bu alanların hepsi
  **`null`**'dır — ders N bölüme ait olabildiği için tek bir değeri yok. `university_*` her
  iki dalda da dolu.
- **Müfredat verisi:** `semesters` (yarıyıl **kümesi**, ör. `[2,3,5]`) ve `is_elective`,
  **(ders, bölüm)** ikilisine aittir — aynı ders bir bölümde zorunlu, başkasında seçmeli
  olabilir. Yalnızca PAÜ derslerinde dolu; diğer üniversitelerde ve admin'in elle açtığı derste
  **`null`** — "zorunlu" ile "bilinmiyor" aynı kova değil, bu yüzden `null` olanlar **hiçbir
  filtre dalında dönmez**. `?is_elective=` `search` dalında **"en az bir bölümde"** anlamındadır.
- ⚠️ `semesters` bir küme, aralık değil: ders arada bir yarıyılda açılmıyor olabilir. Etiket ve
  sıralama içindir, **sınıf filtresi olarak kullanılmamalı** — alttan/üstten ders yüzünden
  öğrencinin ders listesi rutin olarak kendi sınıfının dışına taşar, `GET /users/me`'deki
  `current_grade` de kayıt yılından hesaplanan bir tahmindir.
- ⚠️ `POST /courses` `department_id` alır ama aynı üniversitede aynı `(kod, ad)` ders varsa
  **yeni ders açmaz**, o dersi bölümün müfredatına ekler (ders zaten o bölümdeyse 400).
  `PATCH /courses/{id}` yalnızca `name`/`code` alır ve değişiklik dersin listelendiği **tüm**
  bölümleri etkiler; `DELETE` de dersi tüm bölümlerden düşürür.
- Üniversitelerin `city` alanı gerçek veri (YÖK Atlas). KKTC/yurtdışı üniversitelerde biçim
  `"Lefkoşa (KKTC)"` / `"Bakü (Azerbaycan)"` — düz il adı varsayılmamalı.
- Ortalamalar **her zaman** yalnızca `approved` review'lardan hesaplanır (admin görüntülemesinde
  bile); admin diğer statüleri `GET /reviews?status=` ile ayrıca listeler.

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

## 11. Admin metrik uçları

İkisi de **admin**: `GET /admin/stats` (anlık durum) ve `GET /admin/stats/events` (olay
sayaçları). ⚠️ İkisi de **`Page[T]` zarfı kullanmaz** — liste değil, düz nesne dönerler.

- `/admin/stats` blokları: `users` (toplam / doğrulanmış / rol / kayıt yılı), `content` (aktif
  üniversite→ders-hoca sayıları), `data_health` (hocasız ders, müfredatı boş ders-bölüm bağı),
  `moderation` (review + rapor statü kırılımı, bekleyen düzenleme, süresi geçmemiş kayıt ve
  şifre sıfırlama OTP'leri ayrı ayrı).
  Her çağrı canlı sorgudur, önbellek yok (ölçülen toplam süre 10-35 ms).
- ⚠️ **Bölüm/üniversite kırılımı bilinçli olarak YOK**: tek kullanıcılı bir bölümün sayısı o
  kullanıcının yorumlarını kimliklendirebilirdi. Aynı sebeple hiçbir metrik yanıtında `user_id`,
  e-posta veya review↔kullanıcı eşleşmesi bulunmaz.
- `/admin/stats/events?days=30` (`days` 1..365) gün × olay matrisi döner: `series` pencerenin
  **her** gününü, `counts` bilinen **her** olayı içerir (veri yoksa `0`) — istemci boşluk
  doldurmaz. `totals` pencere toplamıdır. Gün sınırı **UTC**.
- ⚠️ **Sayaçlar geçmişe dönük değildir**, yalnızca kod devreye girdikten sonrasını görür.
  `first_recorded_day` ilk kaydın günüdür; ondan öncesindeki `0`'lar "olmadı" değil
  **"ölçülmedi"** demektir — grafik bu tarihten öncesini kesmeli.
- Olay adları `alan.olay` biçiminde: `auth.login_failed`, `mail.verification_sent`,
  `review.created`, `report.resolved`, `moderation.rejected` … Liste kodda sabittir ama
  büyüyebilir; istemci `events` dizisini okumalı, sabit anahtar kümesi varsaymamalı.
- ⚠️ `moderation.failed` (HF'e ulaşılamadı) `moderation.pending`'in **alt kümesidir**: karar
  verilemeyen yorum pending'e düşer, iki sayaç birden artar.
- `mail.failed` `mail.*_sent` sayaçlarının alt kümesi **değildir**: gönderilemeyen mail
  "gönderildi" sayılmaz, yalnızca `mail.failed` artar.

## 12. Dağıtım

Sözleşme dışı; `docs/deployment.md` (yerel docker) ve `docs/deploy-plan.md` (prod).
