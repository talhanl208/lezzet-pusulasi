# Yayınlama: GitHub → PythonAnywhere → telefon

Kod GitHub'da durur, uygulama PythonAnywhere'de çalışır, telefona da oradaki adres eklenir.
**API anahtarları hiçbir zaman GitHub'a gitmez**: sadece sunucudaki `.env` dosyasında durur.

---

## 1. GitHub'a yükleme

1. GitHub'da **New repository** → ad: `lezzet-pusulasi` → Public ya da Private.
   README, .gitignore veya lisans **ekleme**; projede zaten var.
2. Proje klasöründe terminal aç (VS Code → Terminal) ve sırayla:

```bash
git init
git add .
git status
```

3. **Durup kontrol et.** `git status` listesinde şunlar **olmamalı**:
   - `.env`
   - `instance/` (veritabanı)

   Emin olmak için:

```bash
git check-ignore -v .env          # ".gitignore:1:.env  .env" yazmalı
git grep -nE "AIza[0-9A-Za-z_-]{30}"       # Google anahtarı arar → hiçbir sonuç çıkmamalı
git grep -nE "sk-ant-[A-Za-z0-9_-]{20}"    # Anthropic anahtarı arar → hiçbir sonuç çıkmamalı
```

4. Her şey temizse:

```bash
git commit -m "Lezzet Pusulası ilk sürüm"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/lezzet-pusulasi.git
git push -u origin main
```

5. GitHub sayfasını aç ve dosya listesinde `.env` olmadığını gözünle de doğrula.

> Yanlışlıkla bir anahtar GitHub'a gittiyse dosyayı silmek yetmez (geçmişte kalır).
> Hemen Google Cloud / Anthropic konsolundan **o anahtarı sil, yenisini oluştur**.

---

## 2. PythonAnywhere'de yayınlama (ücretsiz)

Ücretsiz hesapla adresin `https://KULLANICI_ADIN.pythonanywhere.com` olur.

Ücretsiz hesabın sınırları:
- Ayda bir giriş yapıp Web sekmesindeki **"Run until 1 month from today"** düğmesine basman gerekir, yoksa site durdurulur.
- Dışarıya sadece izinli sitelere bağlanılır. Google ve Claude API'leri izinli; SerpApi değil, o yüzden derin analiz orada çalışmaz.
- Arka plan thread'leri yok. Bu yüzden `.env`'de `ARKA_PLAN_ISLERI=0` olmalı: tarama birkaç saniye sayfada bekletir, Claude özeti her mekan ilk açıldığında yapılır.

### 2.1 Hesap ve kod

1. [pythonanywhere.com](https://www.pythonanywhere.com/) → **Pricing & signup** → **Create a Beginner account**.
   Seçtiğin kullanıcı adı site adresin olur.
2. **Consoles** → **Bash** konsolu aç:

```bash
git clone https://github.com/KULLANICI_ADIN/lezzet-pusulasi.git
cd lezzet-pusulasi
python3 -m venv ~/pusula-venv
source ~/pusula-venv/bin/activate
pip install -r requirements.txt
python --version                  # bu sürümü not et (ör. 3.11)
```

### 2.2 `.env` dosyası (sadece sunucuda)

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # çıkanı SECRET_KEY'e yapıştır
nano .env
```

Doldurulacaklar:

```
SECRET_KEY=yukarıda üretilen metin
APP_SIFRESI=kendi belirleyeceğin güçlü bir şifre
GOOGLE_PLACES_API_KEY=Google anahtarın
ANTHROPIC_API_KEY=varsa Claude anahtarın
ARKA_PLAN_ISLERI=0
HTTPS=1
```

`Ctrl+O`, Enter ile kaydet, `Ctrl+X` ile çık. Sonra dosyayı sadece senin okuyabileceğin hale getir:

```bash
chmod 600 .env
```

### 2.3 Web uygulaması

1. **Web** sekmesi → **Add a new web app** → Next → **Manual configuration** (Flask hızlı kurulumunu değil) → not ettiğin Python sürümü → Next.
2. Aynı sayfada:
   - **Source code:** `/home/KULLANICI_ADIN/lezzet-pusulasi`
   - **Virtualenv:** `/home/KULLANICI_ADIN/pusula-venv`
   - **Force HTTPS:** açık
   - **Static files:** URL `/static/` → Directory `/home/KULLANICI_ADIN/lezzet-pusulasi/pusula/static`
3. **WSGI configuration file** bağlantısına tıkla, içindekilerin **hepsini sil** ve şunu yapıştır:

```python
import sys

yol = "/home/KULLANICI_ADIN/lezzet-pusulasi"
if yol not in sys.path:
    sys.path.insert(0, yol)

from app import app as application
```

4. Kaydet, Web sekmesine dön, yeşil **Reload** düğmesine bas.
5. `https://KULLANICI_ADIN.pythonanywhere.com` adresini aç, şifreyle giriş yap, bir şehir tara.

Hata olursa: Web sekmesindeki **Error log** bağlantısının son satırları sorunu söyler.

### 2.4 Güncelleme (kodu değiştirdiğinde)

Bilgisayarında `git push` yaptıktan sonra PythonAnywhere Bash konsolunda:

```bash
cd ~/lezzet-pusulasi && git pull
```

Ardından Web sekmesinde **Reload**.

---

## 3. Telefonun ana ekranına ekleme

- **Android (Chrome):** siteyi aç → sağ üstteki **⋮** → **Ana ekrana ekle** ya da **Uygulamayı yükle**.
- **iPhone (Safari):** siteyi aç → **Paylaş** düğmesi → **Ana Ekrana Ekle**.

Simgesi pusula olan "Pusula" uygulaması ana ekrana gelir ve tarayıcı çubuğu olmadan tam ekran açılır.
Giriş 30 gün hatırlanır.

---

## Güvenlik kontrol listesi

- [ ] `.env` GitHub'da yok (`git check-ignore -v .env`)
- [ ] `APP_SIFRESI` dolu ve tahmin edilmesi zor
- [ ] Google anahtarı sadece **Places API (New)** ile kısıtlı
- [ ] Google Cloud'da bütçe uyarısı kurulu
- [ ] `.env`'de `GUNLUK_ARAMA_LIMITI` / `GUNLUK_FOTO_LIMITI` makul (varsayılan 200 / 300)
- [ ] (Harita için) `GOOGLE_MAPS_JS_KEY` ayrı bir anahtar ve **Web siteleri** kısıtlamasıyla sadece `KULLANICI_ADIN.pythonanywhere.com` adresine izinli.
      Bu anahtar tarayıcıda görünür; bu normal, kısıtlama onu korur.
