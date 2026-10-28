"""API anahtarı olmadan uygulamayı denemek için sahte (demo) veri üretir.

Mekan adları, yorumlar ve menüler tamamen uydurmadır ve arayüzde her yerde "demo"
olarak işaretlenir. Aynı şehir için her seferinde aynı veriyi üretir (sabit tohum).
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from ..kategori import kategori_belirle

ISIMLER = ["Kemal", "Rıza", "Necati", "Sabri", "Halil", "Ferhat", "Cemil", "Nuri", "Yaşar",
           "Tevfik", "Zeki", "Hüsnü", "Recep", "Şükrü", "Ramazan", "İsmail", "Hayri", "Lütfi"]
YERLER = ["Çınaraltı", "Köprübaşı", "Kale", "Çarşı", "Han", "Meydan", "Liman", "Eski Konak",
          "Asmalı", "Kuyulu", "Avlu", "Pazar", "Saat Kulesi", "Bağlar", "Değirmen", "Taşhan",
          "Yokuş", "Kemeraltı", "Bahçeli", "Sarnıç", "Çeşme", "Hamam", "Kervan", "Kuşluk"]

AD_SABLONLARI = {
    "kebap": ["{i} Usta Ocakbaşı", "{y} Kebap Salonu", "Közde {i} Kebap", "{y} Izgara Kebap"],
    "esnaf": ["{y} Esnaf Lokantası", "{i}'in Yeri Ev Yemekleri", "Tencere {y} Lokantası"],
    "sokak": ["{i} Usta Döner", "{y} Tantuni", "{y} Kokoreç", "Dürümcü {i}"],
    "pide": ["{y} Pide Salonu", "{i} Usta Lahmacun", "Taş Fırın {y} Pide"],
    "fastfood": ["Burger Atölyesi {y}", "Çıtır Burger {y}", "Smash {y} Burger"],
    "pizza": ["Forno {y} Pizza", "{y} Pizzeria", "Odun Ateşi {y} Pizza"],
    "balik": ["{y} Balıkçısı", "Martı {y} Balık", "{i} Reis Balık Evi"],
    "kahvalti": ["{y} Kahvaltı Evi", "Bahçe Serpme {y} Kahvaltı", "{i}'in Gözleme Evi"],
    "kafe": ["{y} Kahve Evi", "Dem {y} Cafe", "{y} Kitap Kafe"],
    "tatli": ["{y} Baklavacısı", "Şerbet {y} Tatlı", "{i} Usta Künefe"],
    "meyhane": ["{y} Meyhanesi", "Asma Altı {y} Meyhane", "Rakı Meze {y} Meyhane"],
    "dunya": ["Wok {y} Asian", "Sakura {y} Sushi", "Ramen Köşe {y} Noodle"],
    "fine": ["Konak {y} Fine Dining", "Atölye {y} Mutfak"],
    "restoran": ["{y} Sofrası Restoran", "Avlu {y} Restoran", "{y} Bahçe Restoran"],
}
DAGILIM = {"kebap": 9, "esnaf": 6, "sokak": 6, "pide": 5, "fastfood": 4, "pizza": 3,
           "balik": 3, "kahvalti": 5, "kafe": 5, "tatli": 4, "meyhane": 3, "dunya": 2,
           "fine": 1, "restoran": 6}
GOOGLE_TURU = {"kebap": "turkish_restaurant", "esnaf": "turkish_restaurant",
               "sokak": "fast_food_restaurant", "pide": "turkish_restaurant",
               "fastfood": "hamburger_restaurant", "pizza": "pizza_restaurant",
               "balik": "seafood_restaurant", "kahvalti": "breakfast_restaurant",
               "kafe": "cafe", "tatli": "dessert_shop", "meyhane": "bar",
               "dunya": "asian_restaurant", "fine": "fine_dining_restaurant",
               "restoran": "restaurant"}
TUR_ADI = {"kebap": "Kebapçı", "esnaf": "Lokanta", "sokak": "Dönerci", "pide": "Pideci",
           "fastfood": "Hamburger restoranı", "pizza": "Pizzacı", "balik": "Balık restoranı",
           "kahvalti": "Kahvaltı restoranı", "kafe": "Kafe", "tatli": "Tatlıcı",
           "meyhane": "Meyhane", "dunya": "Asya restoranı", "fine": "Fine dining restoran",
           "restoran": "Restoran"}
FIYAT_SEVIYESI = {"kebap": 2, "esnaf": 1, "sokak": 1, "pide": 1, "fastfood": 2, "pizza": 2,
                  "balik": 3, "kahvalti": 2, "kafe": 2, "tatli": 2, "meyhane": 3, "dunya": 3,
                  "fine": 4, "restoran": 2}
FIYAT_ARALIGI = {1: (200, 400), 2: (400, 600), 3: (600, 1000), 4: (1000, 2000)}
SEVIYE_CARPANI = {1: 0.72, 2: 1.0, 3: 1.55, 4: 2.6}

# Orta fiyat seviyesinde (₺₺) baz fiyatlar
MENULER = {
    "kebap": [("Adana kebap", 520, "kebap"), ("Urfa kebap", 520, "kebap"), ("Beyti", 590, "kebap"),
              ("Kuzu şiş", 640, "kebap"), ("Tavuk şiş", 380, "kebap"), ("Lahmacun", 160, "pide"),
              ("Mercimek çorbası", 130, "çorba"), ("Künefe", 260, "tatlı"), ("Ayran", 60, "içecek"),
              ("Şalgam", 60, "içecek")],
    "esnaf": [("Mercimek çorbası", 110, "çorba"), ("Kuru fasulye", 210, "ana yemek"),
              ("Pilav", 90, "ana yemek"), ("Karnıyarık", 240, "ana yemek"),
              ("Etli nohut", 220, "ana yemek"), ("Hünkar beğendi", 380, "ana yemek"),
              ("Tavuk sote", 250, "ana yemek"), ("Sütlaç", 120, "tatlı"), ("Ayran", 50, "içecek")],
    "sokak": [("Et döner dürüm", 330, "ana yemek"), ("Tavuk döner dürüm", 210, "ana yemek"),
              ("Tantuni", 260, "ana yemek"), ("Kokoreç (yarım)", 280, "ana yemek"),
              ("İskender", 480, "ana yemek"), ("Çiğ köfte dürüm", 120, "ana yemek"),
              ("Ayran", 50, "içecek")],
    "pide": [("Kıymalı pide", 320, "pide"), ("Kuşbaşılı pide", 420, "pide"),
             ("Kaşarlı pide", 280, "pide"), ("Lahmacun", 150, "pide"), ("Etli ekmek", 380, "pide"),
             ("Künefe", 240, "tatlı"), ("Ayran", 50, "içecek")],
    "fastfood": [("Klasik burger", 390, "ana yemek"), ("Cheeseburger", 430, "ana yemek"),
                 ("Tavuk burger", 330, "ana yemek"), ("Patates kızartması", 140, "diğer"),
                 ("Soğan halkası", 150, "diğer"), ("Kola", 80, "içecek")],
    "pizza": [("Margherita", 380, "ana yemek"), ("Karışık pizza", 480, "ana yemek"),
              ("Sucuklu pizza", 450, "ana yemek"), ("Kremalı makarna", 360, "ana yemek"),
              ("Tiramisu", 230, "tatlı"), ("Limonata", 110, "içecek")],
    "balik": [("Levrek ızgara", 690, "ana yemek"), ("Çipura ızgara", 690, "ana yemek"),
              ("Hamsi tava", 420, "ana yemek"), ("Kalamar tava", 520, "meze"),
              ("Midye tava", 340, "meze"), ("Mevsim salata", 160, "salata")],
    "kahvalti": [("Serpme kahvaltı (kişi)", 650, "kahvaltı"), ("Menemen", 220, "kahvaltı"),
                 ("Sucuklu yumurta", 260, "kahvaltı"), ("Peynirli gözleme", 190, "kahvaltı"),
                 ("Su böreği", 210, "kahvaltı"), ("Demlik çay", 140, "içecek"),
                 ("Türk kahvesi", 110, "içecek")],
    "kafe": [("Türk kahvesi", 110, "içecek"), ("Latte", 160, "içecek"),
             ("Filtre kahve", 140, "içecek"), ("Cheesecake", 230, "tatlı"),
             ("Waffle", 290, "tatlı"), ("Kaşarlı tost", 210, "diğer"), ("Limonata", 120, "içecek")],
    "tatli": [("Fıstıklı baklava (porsiyon)", 420, "tatlı"), ("Künefe", 280, "tatlı"),
              ("Katmer", 360, "tatlı"), ("Sütlaç", 150, "tatlı"), ("Kazandibi", 160, "tatlı"),
              ("Maraş dondurması", 120, "tatlı"), ("Çay", 30, "içecek")],
    "meyhane": [("Soğuk meze tabağı", 420, "meze"), ("Haydari", 140, "meze"),
                ("Acılı ezme", 140, "meze"), ("Kalamar", 450, "meze"),
                ("Levrek buğulama", 620, "ana yemek"), ("Rakı (tek)", 330, "içecek")],
    "dunya": [("Sushi set (12'li)", 780, "ana yemek"), ("Tonkotsu ramen", 520, "ana yemek"),
              ("Tavuklu noodle", 420, "ana yemek"), ("Dim sum", 380, "meze"),
              ("Miso çorbası", 160, "çorba")],
    "fine": [("Tadım menüsü", 3800, "ana yemek"), ("Kuzu incik", 1450, "ana yemek"),
             ("Levrek fileto", 1300, "ana yemek"), ("Çikolatalı sufle", 480, "tatlı")],
    "restoran": [("Izgara köfte", 420, "ana yemek"), ("Tavuk şiş", 380, "ana yemek"),
                 ("Mantı", 380, "ana yemek"), ("Karnıyarık", 290, "ana yemek"),
                 ("Mercimek çorbası", 130, "çorba"), ("Sütlaç", 150, "tatlı"),
                 ("Ayran", 60, "içecek")],
}

ILCELER = {
    34: ["Kadıköy", "Beşiktaş", "Fatih", "Beyoğlu", "Üsküdar", "Şişli"],
    6: ["Çankaya", "Keçiören", "Yenimahalle", "Altındağ"],
    35: ["Konak", "Karşıyaka", "Bornova", "Alsancak"],
}
GENEL_ILCELER = ["Merkez", "Çarşı", "Yenişehir", "Üniversite", "İstasyon"]

SABLON = {
    "lezzet": ([
        "{yemek} gerçekten çok lezzetliydi", "Yemekler enfesti, özellikle {yemek} harika",
        "Lezzet olarak şehirdeki en iyilerden", "{yemek} tam kıvamında, ustanın eline sağlık",
        "Malzemeler taze, her şey çok lezzetliydi"], [
        "{yemek} maalesef lezzetsizdi", "Yemekler soğuk geldi, tadı da vasattı",
        "Lezzet beklediğim gibi değildi, idare eder", "{yemek} çok yağlıydı"]),
    "servis": ([
        "Garsonlar çok ilgili ve güler yüzlü", "Personel çok nazik, işletme sahibi bizzat ilgilendi",
        "Servis gayet iyiydi, samimi bir karşılama"], [
        "Garsonlar ilgisiz, birkaç kez çağırmak zorunda kaldık", "Personel oldukça kaba davrandı",
        "Servis kötüydü, siparişi yanlış getirdiler"]),
    "fiyat_performans": ([
        "Fiyatlar gayet uygun, porsiyonlar doyurucu", "Fiyat/performans olarak çok iyi",
        "Bu lezzete bu fiyat çok makul"], [
        "Fiyatlar porsiyona göre pahalı", "Porsiyonlar az geldi, hesap da yüksekti",
        "Fiyatlar biraz pahalı geldi"]),
    "temizlik": ([
        "Mekan tertemiz", "Tuvaletler dahil her yer temiz ve bakımlı"], [
        "Masalar kirliydi, temizliğe dikkat etmiyorlar", "Tuvalet çok kötü durumdaydı",
        "İçeride sinek vardı, hijyen kötü"]),
    "ambiyans": ([
        "Ortam çok keyifli", "Mekan şirin ve ferah, oturması rahat",
        "Ortamı güzel, manzarası da harika"], [
        "İçerisi çok kalabalık ve gürültülüydü", "Masalar sıkışık, rahat edemedik"]),
    "hiz": ([
        "Siparişler çok hızlı geldi", "Kalabalığa rağmen yemekler çabuk geldi"], [
        "Yemek için 45 dakika bekledik", "Servis çok yavaş, uzun süre beklettiler"]),
}
TURIST_YORUMLARI = ["Menüde fiyat yazmıyor, hesap gelince şok olduk, tam bir kazık",
                    "Turistlere farklı fiyat uyguluyorlar, hesabı şişirdiler",
                    "Fahiş fiyat, hesapta sipariş etmediğimiz şeyler vardı"]
GENEL = (["Kesinlikle tavsiye ederim.", "Tekrar geleceğiz.", "Şehre gelen herkese öneririm."],
         ["Bir daha gelmem.", "Tavsiye etmem.", "Hayal kırıklığı oldu."])
PRATIK = ["Kart geçmiyor, sadece nakit çalışıyorlar.", "Akşamları rezervasyon şart, yer bulamadık.",
          "Otopark yok, park yeri bulmak zor.", "Öğle saatlerinde kuyruk oluyor."]
KIMLERE = ["Ailecek geldik, çocuklar için de uygun.", "Arkadaşlarla gelmek için ideal.",
           "Eşimle romantik bir akşam yemeği için geldik."]
GUNLER = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"]
SAAT_PROFILI = {
    "kahvalti": (7, 0, 16, 0), "kafe": (8, 0, 24, 0), "meyhane": (17, 0, 26, 0),
    "sokak": (10, 0, 27, 0), "esnaf": (6, 30, 17, 0), "tatli": (8, 0, 24, 0),
}


def _saatler(kod: str, r: random.Random):
    if kod == "sokak" and r.random() < 0.15:
        return [{"open": {"day": 0, "hour": 0, "minute": 0}}], [
            f"{GUNLER[(i + 1) % 7]}: 24 saat açık" for i in range(7)]
    ah, am, kh, km = SAAT_PROFILI.get(kod, (11, 0, 23, 0))
    kapali = 0 if kod == "esnaf" else (1 if r.random() < 0.15 else None)
    periyotlar, yazilar = [], []
    for gun in range(7):
        if gun == kapali:
            continue
        kapanis_gun = (gun + kh // 24) % 7
        periyotlar.append({"open": {"day": gun, "hour": ah, "minute": am},
                           "close": {"day": kapanis_gun, "hour": kh % 24, "minute": km}})
    for i in range(7):
        gun = (i + 1) % 7  # Pazartesi'den başla
        yazilar.append(f"{GUNLER[gun]}: Kapalı" if gun == kapali
                       else f"{GUNLER[gun]}: {ah:02d}:{am:02d}–{kh % 24:02d}:{km:02d}")
    return periyotlar, yazilar


def _sinirla(x, a, b):
    return max(a, min(b, x))


def _yorum_yaz(r: random.Random, ozellik: dict, yemekler: list[str], seviye: int,
               turist: bool) -> tuple[str, int]:
    konular = r.sample(list(SABLON), k=r.choice([1, 2, 2, 3]))
    cumleler, puanlar = [], []
    for konu in konular:
        deger = ozellik[konu] + r.gauss(0, 1.3)
        puanlar.append(deger)
        olumlu, olumsuz = SABLON[konu]
        if deger >= 6.3:
            cumleler.append(r.choice(olumlu))
        elif deger <= 4.7:
            cumleler.append(r.choice(olumsuz))
    if turist and r.random() < 0.45:
        cumleler.append(r.choice(TURIST_YORUMLARI))
        puanlar.append(2)
    genel = sum(ozellik.values()) / len(ozellik)
    x = (genel + sum(puanlar) / len(puanlar)) / 2
    yildiz = int(round(_sinirla(1.6 + (x - 1) * 0.444 + r.gauss(0, 0.45), 1, 5)))
    if r.random() < 0.35:
        cumleler.append(r.choice(GENEL[0] if yildiz >= 4 else GENEL[1]))
    if r.random() < 0.15:
        cumleler.append(r.choice(PRATIK))
    if r.random() < 0.12:
        cumleler.append(r.choice(KIMLERE))
    if r.random() < 0.12:
        tutar = int(FIYAT_ARALIGI[seviye][0] * r.uniform(0.9, 1.5) / 10) * 10
        cumleler.append(f"Kişi başı {tutar} TL civarı ödedik.")
    if not cumleler:
        cumleler.append(r.choice(GENEL[0] if yildiz >= 4 else GENEL[1]))
    metin = ". ".join(c.rstrip(".").format(yemek=r.choice(yemekler)) for c in cumleler) + "."
    return metin[0].upper() + metin[1:], yildiz


def sehir_mekanlari(il: dict, bugun: date | None = None) -> list[dict]:
    """Bir il için ~60 demo mekan kaydı (Google dönüştürücüsüyle aynı biçimde)."""
    bugun = bugun or date.today()
    r = random.Random(il["plaka"] * 7919)
    sahil = il["plaka"] in (34, 35, 7, 33, 61, 53, 55, 48, 9, 17, 10, 57, 52, 28, 22, 59, 77, 41)
    dagilim = dict(DAGILIM)
    if sahil:
        dagilim["balik"] += 3
        dagilim["meyhane"] += 1
    ilceler = ILCELER.get(il["plaka"], GENEL_ILCELER)
    kayitlar, kullanilan = [], set()
    sira = 0
    for kod, adet in dagilim.items():
        yemek_adlari = [ad for ad, _, k in MENULER[kod] if k not in ("içecek",)]
        for _ in range(adet):
            sira += 1
            for _deneme in range(30):
                ad = r.choice(AD_SABLONLARI[kod]).format(i=r.choice(ISIMLER), y=r.choice(YERLER))
                if ad not in kullanilan:
                    break
            kullanilan.add(ad)

            profil = r.random()
            turist = profil < 0.08
            gizli = 0.08 <= profil < 0.18
            kalite = _sinirla(r.gauss(7.0, 1.3), 3.2, 9.6)
            if gizli:
                kalite = r.uniform(8.6, 9.6)
            ozellik = {k: _sinirla(kalite + r.gauss(0, 1.1), 1, 10) for k in SABLON}
            seviye = int(_sinirla(FIYAT_SEVIYESI[kod] + r.choice([0, 0, 0, 1, -1]), 1, 4))
            ozellik["fiyat_performans"] = _sinirla(ozellik["fiyat_performans"] - (seviye - 2) * 0.7,
                                                   1, 10)
            if turist:
                ozellik.update(lezzet=r.uniform(4, 6), fiyat_performans=r.uniform(1.5, 3),
                               servis=r.uniform(3, 5))
            egilim = r.choice([0] * 7 + [1.6, -1.8, -1.8])

            puan = _sinirla(3.0 + (sum(ozellik.values()) / 6 - 3) * 0.29 + r.gauss(0, 0.1), 3.1, 4.9)
            if gizli:
                puan = r.uniform(4.6, 4.9)
                yorum_sayisi = r.randint(30, 300)
            else:
                yorum_sayisi = int(math.exp(r.gauss(6.4, 1.15)))
                if puan >= 4.4 and r.random() < 0.3:
                    yorum_sayisi = r.randint(3000, 15000)

            yorumlar = []
            for n in range(r.randint(8, 14)):
                gun_once = int(r.triangular(2, 720, 60))
                o = dict(ozellik)
                if egilim and gun_once < 180:
                    o = {k: _sinirla(v + egilim, 1, 10) for k, v in o.items()}
                metin, yildiz = _yorum_yaz(r, o, yemek_adlari, seviye, turist)
                yorumlar.append({"kaynak": "demo", "yazar": f"Demo kullanıcı {r.randint(10, 999)}",
                                 "puan": yildiz, "metin": metin,
                                 "tarih": (bugun - timedelta(days=gun_once)).isoformat(),
                                 "dil": "tr"})

            km = abs(r.gauss(0, il["yaricap_km"] * 0.35))
            aci = r.uniform(0, 2 * math.pi)
            lat = il["lat"] + km * math.cos(aci) / 111.0
            lng = il["lng"] + km * math.sin(aci) / (111.0 * math.cos(math.radians(il["lat"])))
            periyotlar, saat_yazilari = _saatler(kod, r)
            fmin, fmax = FIYAT_ARALIGI[seviye] if r.random() < 0.5 else (None, None)

            menu_var = r.random() < 0.75
            menu_ay = r.choice([1, 2, 3, 5, 7, 9, 14, 20]) if menu_var else None
            fotolar = [{"kaynak": "demo", "ref": f"demo:{kod}:{sira}:yemek:{i}", "kategori": "yemek",
                        "yazar": "Demo", "sira": i} for i in range(r.randint(2, 4))]
            fotolar.insert(1, {"kaynak": "demo", "ref": f"demo:{kod}:{sira}:mekan:0",
                               "kategori": "mekan", "yazar": "Demo", "sira": 1})
            if menu_var:
                fotolar.append({"kaynak": "demo", "ref": f"demo:{kod}:{sira}:menu:0", "kategori": "menu",
                                "menu_mu": 1, "yazar": "Demo", "sira": 9,
                                "yukleme_tarihi": (bugun - timedelta(days=int(menu_ay * 30.4))).isoformat()})
            enflasyon = max(0.45, 1 - 0.028 * (menu_ay or 0))
            urunler = [{"ad": ad, "kategori": k,
                        "fiyat": int(round(f * SEVIYE_CARPANI[seviye] * enflasyon * r.uniform(0.92, 1.08), -1))}
                       for ad, f, k in MENULER[kod]]

            kayitlar.append({
                "place_id": f"demo-{il['plaka']}-{sira}",
                "ad": ad,
                "adres": f"{r.choice(YERLER)} Mah. {r.randint(1, 140)}. Sok. No:{r.randint(1, 60)}, "
                         f"{il['ad']}",
                "ilce": r.choice(ilceler),
                "lat": round(lat, 6), "lng": round(lng, 6),
                "google_puan": round(puan, 1),
                "yorum_sayisi": yorum_sayisi,
                "fiyat_seviyesi": seviye,
                "fiyat_min": fmin, "fiyat_max": fmax,
                "turler": [GOOGLE_TURU[kod], "restaurant", "food"],
                "birincil_tur": GOOGLE_TURU[kod],
                "birincil_tur_adi": TUR_ADI[kod],
                "kategori": kategori_belirle(ad, [GOOGLE_TURU[kod]], GOOGLE_TURU[kod], seviye),
                "telefon": f"0{r.randint(212, 488)} {r.randint(200, 999)} {r.randint(10, 99)} {r.randint(10, 99)}",
                "web": None,
                "maps_url": None,
                "calisma_saatleri": saat_yazilari,
                "saat_periyotlari": periyotlar,
                "isletme_durumu": "OPERATIONAL",
                "google_ozet": None,
                "google_ozet_aciklama": None,
                "ozellikler": {
                    "vejetaryen": r.random() < (0.7 if kod in ("kafe", "pizza", "kahvalti", "esnaf") else 0.25),
                    "paket": r.random() < 0.8, "teslimat": r.random() < 0.55,
                    "acik_alan": r.random() < 0.45, "cocuk": r.random() < 0.5,
                    "grup": r.random() < 0.6, "rezervasyon": r.random() < (0.85 if seviye >= 3 else 0.3),
                    "alkol": kod in ("meyhane", "balik", "fine") or r.random() < 0.08,
                    "kahvalti": kod in ("kahvalti", "kafe"),
                    "otopark": r.random() < 0.35,
                },
                "yorumlar": yorumlar,
                "fotolar": fotolar,
                "demo_menu": {
                    "durum": "bulundu" if menu_var else "yok",
                    "kaynak": "demo",
                    "urunler": urunler if menu_var else [],
                    "en_yeni_tarih": fotolar[-1].get("yukleme_tarihi") if menu_var else None,
                    "not": "" if menu_var else "Demo verisinde bu mekan için menü fotoğrafı yok.",
                },
            })
    return kayitlar

