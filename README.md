# 🎓 Kürsü

**Kürsü**, öğrencilerin aldıkları dersler ve akademisyenler hakkında **anonim olarak** yorum yapıp puan verebildiği, topluluk odaklı bir akademik değerlendirme platformudur. Kullanıcılar hoca ismiyle arama yaparak geçmiş öğrencilerin deneyimlerini (ders anlatımı, sınav zorluğu, notlandırma tarzı vb.) inceleyebilir.

Bu proje, öğrencilerin hem ders seçim sürecinde hem de üniversite tercih döneminde daha bilinçli kararlar almasını sağlamayı ve akademik geri bildirim kültürünü şeffaf, güvenli bir ortamda güçlendirmeyi hedefler.

---

##  Öne Çıkan Özellikler

-  **Akıllı Arama** — Hoca veya ders ismiyle hızlı ve anlık arama
-  **Çok Boyutlu Puanlama** — Ders anlatımı, sınav zorluğu, notlandırma tarzı gibi kriterlere göre değerlendirme
-  **Tam Anonimlik** — Kullanıcı kimliği hiçbir şekilde yorumlarla ilişkilendirilmez
-  **AI Destekli Moderasyon** — Küfür, hakaret veya nefret söylemi içeren yorumların otomatik tespiti ve filtrelenmesi
-  **Ders & Hoca Profilleri** — Geçmiş dönemlere ait yorum ve puan geçmişinin tutulması
  
---

##  Teknolojik Yığın

| Katman | Teknoloji | Açıklama |
|--------|-----------|----------|
| **Frontend** | React.js + Tailwind CSS | Arama arayüzü, hoca detay sayfalarının render edilmesi |
| **Backend** | FastAPI | Yüksek performanslı, asenkron API yapısı ve otomatik Swagger/OpenAPI dokümantasyonu |
| **Veritabanı** | PostgreSQL | Hocalar, dersler, yorumlar ve puanlar arasındaki ilişkisel veri yapısının yönetimi |
| **Yapay Zeka** | GPT-4o-mini / Hugging Face | Yorumların duygu analizi, küfür/hakaret filtrelemesi |

---

##  Yerel Kurulum Adımları

Aşağıdaki adımlar backend'i (FastAPI + PostgreSQL) lokalde ayağa kaldırır. Tüm komutlar
**`backend/` dizininden** çalıştırılır — uygulama `.env` dosyasını relative yoldan okur.

**Ön koşullar:** Python 3.10+, çalışan bir PostgreSQL sunucusu ve proje için oluşturulmuş boş
bir veritabanı.

```bash
# 1. Sanal ortam (proje kökünde)
python -m venv .venv
source .venv/bin/activate

# 2. Bağımlılıklar
pip install -r backend/requirements.txt

# 3. Ortam değişkenleri
cd backend
cp .env.example .env
#    .env içindeki DATABASE_URL, SECRET_KEY, EMAIL_PEPPER_KEY doldurulur.
#    Açıklamalar ve varsayılanlar için .env.example'a bakınız.

# 4. Veritabanı şeması
alembic upgrade head

# 5. Sunucu
uvicorn main:app --reload
```

Sunucu `http://127.0.0.1:8000` adresinde çalışır; `GET /health` sağlık kontrolü, `/docs`
Swagger arayüzüdür.

> **Not:** E-posta gönderimi henüz gerçek değil (`app/services/email_service.py` `print()`
> stub'ı). Kayıt akışını lokalde denerken OTP kodu **backend konsoluna** yazılır.

##  API Dokümantasyonu

- **[docs/api-contract.md](docs/api-contract.md)** — API sözleşmesi: auth akışı, `Page[T]` liste
  zarfı, maskeleme kuralları, review moderasyon döngüsü, hata gövdeleri ve bilinen kısıtlar.
  Frontend entegrasyonuna buradan başlanır.
- **[docs/openapi.json](docs/openapi.json)** — makine okunur OpenAPI şeması (tip üretimi için).
- Canlı, etkileşimli dokümantasyon: sunucu çalışırken `http://127.0.0.1:8000/docs`.

## Veritabanı Şeması
 
Aşağıda platformun temel varlık-ilişki diyagramı (ERD) yer almaktadır. Diyagramı canlı ve etkileşimli olarak görüntülemek için:
 
**[Veritabanı Şemasını Görüntüle](https://golcuksinan.github.io/K-rs-/database-schema.html)**
 
(veya `docs/database-schema.html` dosyasını indirip herhangi bir tarayıcıda açabilirsiniz)
 
### Temel Varlıklar
 
- **University / Department / Course** — üniversite, bölüm ve ders hiyerarşisi
- **Professor / CourseProfessor** — bir hocanın hangi dersi hangi dönemde verdiği
- **User** — platform kullanıcıları (e-posta doğrulamalı)
- **Review** — kullanıcıların bir ders-hoca kombinasyonuna verdiği puanlar (öğretim, zorluk, adalet) ve yorum
- **Report** — bir değerlendirmenin şikayet edilmesi durumunda tutulan kayıt

## 📄 Lisans

Bu proje eğitim amaçlı bir üniversite topluluğu projesidir. Lisans bilgisi için `LICENSE` dosyasına bakınız.
