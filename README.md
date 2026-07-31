# Kürsü

**Kürsü**, öğrencilerin aldıkları dersler ve akademisyenler hakkında **anonim olarak** yorum yapıp puan verebildiği, topluluk odaklı bir akademik değerlendirme platformudur. Kullanıcılar hoca ismiyle arama yaparak geçmiş öğrencilerin deneyimlerini (ders anlatımı, sınav zorluğu, notlandırma tarzı vb.) inceleyebilir.

Bu proje, öğrencilerin hem ders seçim sürecinde hem de üniversite tercih döneminde daha bilinçli kararlar almasını sağlamayı ve akademik geri bildirim kültürünü şeffaf, güvenli bir ortamda güçlendirmeyi hedefler.

---

## Öne Çıkan Özellikler

- **Akıllı Arama** — Hoca veya ders ismiyle hızlı ve anlık arama
- **Çok Boyutlu Puanlama** — Ders anlatımı, sınav zorluğu, notlandırma tarzı gibi kriterlere göre değerlendirme
- **Tam Anonimlik** — Kullanıcı kimliği hiçbir şekilde yorumlarla ilişkilendirilmez
- **AI Destekli Moderasyon** — Küfür, hakaret veya nefret söylemi içeren yorumların yayın öncesi taranması
- **Ders & Hoca Profilleri** — Geçmiş dönemlere ait yorum ve puan geçmişinin tutulması

---

## Teknolojik Yığın

| Katman | Teknoloji | Açıklama |
|--------|-----------|----------|
| **Frontend** | React.js + Tailwind CSS | Arama arayüzü, hoca detay sayfalarının render edilmesi |
| **Backend** | FastAPI | Yüksek performanslı, asenkron API yapısı ve otomatik Swagger/OpenAPI dokümantasyonu |
| **Veritabanı** | PostgreSQL | Hocalar, dersler, yorumlar ve puanlar arasındaki ilişkisel veri yapısının yönetimi |
| **Yapay Zeka** | Hugging Face — `unitary/toxic-bert` | Yorumların toksisite analizi, küfür/hakaret içerenlerin otomatik moderasyonu |

---

## Veritabanı Şeması

Aşağıda platformun temel varlık-ilişki diyagramı (ERD) yer almaktadır. Diyagramı canlı ve etkileşimli olarak görüntülemek için:

**[Veritabanı Şemasını Görüntüle](https://golcuksinan.github.io/K-rs-/database-schema.html)**

(veya `docs/database-schema.html` dosyasını indirip herhangi bir tarayıcıda açabilirsiniz)

## Lisans

Bu proje eğitim amaçlı bir üniversite topluluğu projesidir. Lisans bilgisi için `LICENSE` dosyasına bakınız.
