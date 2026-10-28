# Lezzet Pusulası 🧭

Şehir dışına çıktığında "nerede yesek?" sorusunu tek ekranda çözen web uygulaması. Türkiye'deki 81 ilden birini yaz; oradaki restoranları Google puanları ve yorumlarıyla toplar, yorumları okuyup **artı/eksi** çıkarır, menü fotoğraflarını bulup **kaç ay önce yüklendiğini** gösterir ve hepsini kendi puan sistemimiz olan **Pusula Puanı** ile sıralar.

## Özellikler

| | |
|---|---|
| **Şehir tarama** | 81 il (plaka kodu da olur: `42`), istersen semt/ilçe (`Kadıköy`). Varsayılan 50 mekan, 30–120 arası seçilebilir. |
| **Yorum analizi** | Her mekan için özet, artılar, eksiler, öne çıkan yemekler, pratik uyarılar (nakit, rezervasyon, park), kimlere uygun. Claude anahtarı varsa Claude, yoksa Türkçe kural tabanlı analiz. |
| **Pusula Puanı** | Yorum sayısına göre güvenilir hale getirilmiş Google puanı + yorumlardan çıkan 6 kriter (lezzet, fiyat/performans, servis, temizlik, ortam, hız) + son 6 ay eğilimi. Kriter ağırlıklarını kullanıcı kaydırıcılarla değiştirir. |
| **Menü** | Fotoğraflarda menüyü bulur, ürün ve fiyatları tabloya çıkarır, menü fotoğrafının yaşını gösterir; 1 yıldan eskiyse uyarır. |
| **Kategoriler** | Kebap & köfte, esnaf lokantası, döner & sokak lezzeti, pide & lahmacun, fast food, balık, kahvaltı, kafe, tatlı, meyhane, dünya mutfağı, fine dining... |
| **Filtre ve sıralama** | Tür, fiyat (₺–₺₺₺₺), en az puan, yorum sayısı, şu an açık, vejetaryen/paket/alkol vb., ilçe, en fazla km. Pusula/Google puanı, yorum sayısı, fiyat, yakınlık. |
| **Konum** | Uzaklık şehir merkezine, tarayıcı konumuna ya da haritada seçilen noktaya (ör. otelin) göre hesaplanır. |
| **Rozetler** | 💎 Gizli hazine, 🔥 Şehrin favorisi, 📈 Yükselişte, 📉 Düşüşte, ⚠️ Turist tuzağı riski, 💸 Cebe uygun, 🧽 Temizlik şikayeti, 🕰️ Menü eski |
| **Mobil** | Telefonun ana ekranına uygulama gibi eklenir (PWA); internete açıkken şifreli giriş. |
| **Ekstralar** | "Buraya gelmişken" yöresel lezzet kısayolları (Konya → etli ekmek...), mekan/yemek araması (menü ve yorumların içinde de arar), "Bugün ne yesek?" rastgele seçici, 3 mekanı yan yana karşılaştırma, gezi listesi + kısaltılmış rota + Google Haritalar yol tarifi, CSV dışa aktarma. |

## Hızlı başlangıç (demo, anahtar gerekmez)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

`http://127.0.0.1:5000` adresine gidip bir şehir yaz. Anahtar yokken uygulama **demo verisi** üretir: mekan adları, yorumlar ve menüler uydurmadır ve her yerde "demo" olarak işaretlidir. Arayüzün ve puanlamanın tamamını bu modda deneyebilirsin.

## Yayınlama ve telefona ekleme

GitHub'a yükleme, PythonAnywhere'de ücretsiz yayınlama ve telefonun ana ekranına ekleme adımları için **[YAYINLAMA.md](YAYINLAMA.md)**.

## Gerçek veriye geçiş

`.env.example` dosyasını `.env` olarak kopyala ve doldur.

### 1. Google Places API (zorunlu)

1. [Google Cloud Console](https://console.cloud.google.com/)'da proje aç, faturalandırma hesabı bağla (ücretsiz kota için de gerekli).
2. **Places API (New)**'ı etkinleştir, bir API anahtarı oluştur, anahtarı sadece Places API (New) ile kısıtla.
3. `.env` → `GOOGLE_PLACES_API_KEY=...`

**Maliyet:** Yorumlar ve fotoğraflar ayrı ayrı istenmez; tek bir "Text Search" isteğinde 20 mekan yorumlarıyla birlikte gelir. Bir şehir taraması genelde 4–8 istek harcar. Bu istekler "Text Search Enterprise + Atmosphere" kalemine düşer; bu kalemde ayda 1.000 istek ücretsiz. Fotoğraf gösterimi "Place Details Photos" kalemindedir, o da ayda 1.000 ücretsiz. Güncel fiyatlar: [Google Maps Platform fiyatlandırması](https://developers.google.com/maps/billing-and-pricing/pricing).

**Fatura güvenliği:** Uygulamanın kendi günlük sayacı var: Google'a günde en fazla `GUNLUK_ARAMA_LIMITI` (200) arama ve `GUNLUK_FOTO_LIMITI` (300) fotoğraf isteği gönderir, sınır dolunca istek atmayı bırakır (sayaç gece yarısı sıfırlanır). Bunun yanında Cloud Console'da bütçe uyarısı kur; ücretli hesaba geçtiysen Kotalar sayfasından günlük kota da koyabilirsin.

**Resmi API'nin sınırları:** mekan başına en fazla 5 yorum ve 10 fotoğraf verir, fotoğrafların yüklenme tarihini vermez. Daha fazlası için aşağıdaki SerpApi seçeneği var.

### 2. Harita (isteğe bağlı)

Google'ın kullanım şartları Places verisinin Google dışı bir haritada gösterilmesini yasaklıyor; bu yüzden gerçek veride harita Google Maps ile çizilir (demo modunda OpenStreetMap kullanılır).

- Cloud Console'da **Maps JavaScript API**'yi etkinleştir, ayrı bir anahtar oluştur ve **HTTP referrer** ile kendi alan adına kısıtla (bu anahtar tarayıcıda görünür).
- `.env` → `GOOGLE_MAPS_JS_KEY=...` (`GOOGLE_MAP_ID` için kendi Map ID'ni oluşturabilirsin; `DEMO_MAP_ID` geliştirme için çalışır.)

### 3. Claude (önerilir)

`.env` → `ANTHROPIC_API_KEY=...` ([console.anthropic.com](https://console.anthropic.com/))

- Yorumları çok daha isabetli özetler ve kriter puanı verir.
- Mekan fotoğraflarında menüyü bulur, ürünleri ve fiyatları okur. Şehir taranırken en iyi `MENU_TARAMA_LIMITI` (varsayılan 8) mekanda otomatik yapılır; diğerlerinde mekan sayfasındaki "Fotoğraflarda menü ara" düğmesiyle.
- Varsayılan model `claude-haiku-5-5` (hızlı ve ucuz). `CLAUDE_MODEL` ile değiştirilebilir.

### 4. SerpApi — derin analiz (isteğe bağlı)

`.env` → `SERPAPI_API_KEY=...` ([serpapi.com](https://serpapi.com/))

Mekan sayfasındaki "Derin analiz" düğmesi en yeni 30 yorumu ve Google Haritalar'daki **Menü** kategorisindeki fotoğrafları **yüklenme tarihleriyle** çeker; sonra tüm yorumlarla analizi yeniler. Mekan başına yaklaşık 6–8 SerpApi araması harcar. Taramada otomatik çalışması için `DERIN_ANALIZ_LIMITI` ayarla (varsayılan 0).

## Pusula Puanı nasıl hesaplanır?

```
Google bileşeni = Bayes ortalaması ile düzeltilmiş puan, 0–10 ölçeğine (3,0★ → 0, 5,0★ → 10)
                  düzeltilmiş = (yorum × puan + 150 × şehir ortalaması) / (yorum + 150)
Kriter bileşeni = 6 kriterin kullanıcı ağırlıklarıyla ortalaması (yorumda kanıt yoksa kriter atlanır)
Eğilim         = son 6 ay ortalaması − genel puan (en fazla ±0,6, az yorumda daha az etkili)

Pusula Puanı   = Google bileşeni × Google payı + Kriter bileşeni × (1 − Google payı) + Eğilim
```

Böylece 12 yorumlu 5,0'lık mekan, 8.000 yorumlu 4,6'lık mekanın önüne geçemez; "fiyat/performans benim için her şey" diyen kullanıcı kendi sıralamasını görür.

## Terminalden tarama

```bash
flask --app app tara konya
flask --app app tara istanbul --hedef 80 --bolge Kadıköy
```

## Testler

```bash
pip install pytest
pytest
```

Dış servisler (Google, Claude, SerpApi) testlerde sahte yanıtlarla çalışır, ağ bağlantısı gerekmez.

## Proje yapısı

```
app.py                      geliştirme sunucusu
pusula/
  __init__.py               uygulama fabrikası, ayarlar, CLI komutu
  web.py                    sayfalar ve uç noktalar
  liste.py                  filtreleme, sıralama, rota
  tarama.py                 şehir tarama akışı, menü tarama, derin analiz
  puanlama.py               Pusula Puanı, rozetler, fiyat
  analiz_kural.py           anahtarsız Türkçe yorum analizi
  yapay_zeka.py             Claude: yorum analizi ve menü okuma
  kaynaklar/google_places.py, serpapi.py, demo.py
  kategori.py, yemekler.py, iller.py (81 il + yöresel lezzetler), konum.py, metin.py
  db.py                     SQLite şeması ve veri erişimi
  isler.py                  arka plan işleri (thread)
  templates/, static/
tests/
```

## Bilmen gerekenler

- **Kazıma yok:** Google Haritalar sayfasını doğrudan kazımak kullanım şartlarına aykırı ve kısa sürede engelleniyor; proje resmi API'yi kullanır.
- **Önbellek:** Google'ın şartları Places içeriğinin uzun süre saklanmasını kısıtlar (place ID hariç). Proje kişisel/portföy kullanımı için veriyi `YENILEME_GUN` (30 gün) boyunca tutar. Herkese açık ya da ticari bir ürüne dönüştürürsen şartları gözden geçir.
- **Atıf:** Google verisi gösterilirken yorum yazarları ve fotoğraf sahipleri sayfada belirtilir, "Google Haritalar'da aç" bağlantısı vardır. Bunları kaldırma.
- **Üretim:** `python app.py` geliştirme içindir. Yayına alırken `gunicorn "app:app"` gibi bir WSGI sunucusu kullan, `SECRET_KEY` ver, arka plan işlerini RQ/Celery gibi bir kuyruğa taşı. Veri büyürse SQLite yerine PostgreSQL'e geçilebilir.

## Geliştirme fikirleri

- Kullanıcı hesabı ve kalıcı gezi listeleri
- Şehirler arası "rota üzerindeki duraklar" (A'dan B'ye giderken yol üstü lokantalar)
- Menü fiyatlarının enflasyona göre bugüne taşınmış tahmini
- Yorum dillerine göre (yerli/turist) ayrı puan
