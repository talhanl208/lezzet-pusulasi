"""Pusula Puanı: Google puanını yorum sayısına göre güvenilir hale getirip,
yorumlardan çıkan kriter puanları ve son dönem eğilimiyle birleştirir.

Puan 0-10 arasıdır. Kullanıcı kriter ağırlıklarını kendisi ayarlayabilir.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from .metin import tarih_coz

KRITERLER = {
    "lezzet": "Lezzet",
    "fiyat_performans": "Fiyat / performans",
    "servis": "Servis",
    "temizlik": "Temizlik",
    "ambiyans": "Ortam",
    "hiz": "Hız",
}
VARSAYILAN_AGIRLIK = {"lezzet": 35, "fiyat_performans": 20, "servis": 15, "temizlik": 15,
                      "ambiyans": 10, "hiz": 5}
VARSAYILAN_GOOGLE_PAYI = 45  # Pusula puanının yüzde kaçı Google puanından gelsin
GUVEN_ESIGI = 150  # Bayes ortalamasında "sanal yorum" sayısı
TREND_GUN = 180

ROZETLER = {
    "gizli_hazine": ("💎", "Gizli hazine", "Az bilinen ama çok beğenilen"),
    "favori": ("🔥", "Şehrin favorisi", "Binlerce yorumla yüksek puan"),
    "yukseliste": ("📈", "Yükselişte", "Son yorumlar genel puandan iyi"),
    "dususte": ("📉", "Düşüşte", "Son yorumlar genel puandan kötü"),
    "turist_tuzagi": ("⚠️", "Turist tuzağı riski", "Fahiş fiyat / hesap şikayetleri var"),
    "uygun_fiyat": ("💸", "Cebe uygun", "Fiyat/performansı güçlü"),
    "temizlik_sorunu": ("🧽", "Temizlik şikayeti", "Hijyenle ilgili olumsuz yorumlar var"),
    "eski_menu": ("🕰️", "Menü eski", "Bulunan menü fotoğrafı 1 yıldan eski"),
}


def agirliklari_duzelt(ham: dict | None) -> tuple[dict, int]:
    """Formdan/oturumdan gelen ağırlıkları doğrular."""
    ham = ham or {}
    agirlik = {}
    for k, v in VARSAYILAN_AGIRLIK.items():
        try:
            agirlik[k] = max(0, min(100, int(ham.get(k, v))))
        except (TypeError, ValueError):
            agirlik[k] = v
    if sum(agirlik.values()) == 0:
        agirlik = dict(VARSAYILAN_AGIRLIK)
    try:
        google_payi = max(0, min(100, int(ham.get("google", VARSAYILAN_GOOGLE_PAYI))))
    except (TypeError, ValueError):
        google_payi = VARSAYILAN_GOOGLE_PAYI
    return agirlik, google_payi


def bayes_puani(puan: float | None, adet: int, sehir_ort: float, m: int = GUVEN_ESIGI):
    """Az yorumlu 5.0'ları şehir ortalamasına doğru çeker (IMDb tarzı)."""
    if puan is None:
        return None
    adet = max(0, adet or 0)
    return (adet * puan + m * sehir_ort) / (adet + m)


def yildizdan_ona(yildiz: float) -> float:
    """3.0 yıldız → 0, 5.0 → 10. Google puanları 3.8-4.8 arasına yığıldığı için
    1-5 doğrusal dönüşüm yerine bu dar aralık ayrımı netleştirir."""
    return max(0.0, min(10.0, (yildiz - 3.0) / 2.0 * 10))


def kriter_bileseni(kriterler: dict | None, agirlik: dict) -> float | None:
    if not kriterler:
        return None
    toplam = payda = 0.0
    for k, w in agirlik.items():
        deger = kriterler.get(k)
        if deger is None or w <= 0:
            continue
        toplam += float(deger) * w
        payda += w
    return toplam / payda if payda else None


def trend_hesapla(yorumlar: list[dict], google_puan: float | None,
                  bugun: date | None = None) -> dict:
    """Son 6 aydaki yorumların ortalaması genel puandan ne kadar farklı?"""
    if not google_puan or not yorumlar:
        return {"fark": None, "adet": 0, "etki": 0.0}
    bugun = bugun or date.today()
    sinir = bugun - timedelta(days=TREND_GUN)
    yeni = [y["puan"] for y in yorumlar
            if y.get("puan") and (t := tarih_coz(y.get("tarih"))) and t >= sinir]
    if len(yeni) < 3:
        return {"fark": None, "adet": len(yeni), "etki": 0.0}
    fark = sum(yeni) / len(yeni) - google_puan
    guven = min(1.0, len(yeni) / 8)
    etki = max(-0.6, min(0.6, fark * 0.4)) * guven
    return {"fark": round(fark, 2), "adet": len(yeni), "etki": round(etki, 2)}


def pusula_puani(mekan: dict, yorumlar: list[dict], sehir_ort: float,
                 agirlik: dict | None = None, google_payi: int | None = None) -> dict:
    """Mekanın Pusula Puanı ve nasıl hesaplandığının dökümü."""
    if agirlik is None or google_payi is None:
        agirlik, google_payi = agirliklari_duzelt(None)
    bayes = bayes_puani(mekan.get("google_puan"), mekan.get("yorum_sayisi") or 0, sehir_ort)
    g = yildizdan_ona(bayes) if bayes is not None else None
    analiz = mekan.get("analiz") or {}
    k = kriter_bileseni(analiz.get("kriterler"), agirlik)
    trend = trend_hesapla(yorumlar, mekan.get("google_puan"))

    if g is None and k is None:
        return {"puan": None, "google": None, "kriter": None, "trend": trend, "bayes": None}
    if g is None:
        temel = k
    elif k is None:
        temel = g
    else:
        oran = google_payi / 100
        temel = g * oran + k * (1 - oran)
    puan = max(0.0, min(10.0, temel + trend["etki"]))
    return {"puan": round(puan, 1), "google": None if g is None else round(g, 1),
            "kriter": None if k is None else round(k, 1), "trend": trend,
            "bayes": None if bayes is None else round(bayes, 2)}


def rozet_belirle(mekan: dict, puan: dict) -> list[str]:
    rozetler = []
    g, adet = mekan.get("google_puan") or 0, mekan.get("yorum_sayisi") or 0
    analiz = mekan.get("analiz") or {}
    kriter = analiz.get("kriterler") or {}
    p = puan.get("puan") or 0
    if g >= 4.6 and 25 <= adet <= 400 and p >= 7.0:
        rozetler.append("gizli_hazine")
    if g >= 4.4 and adet >= 3000:
        rozetler.append("favori")
    fark = (puan.get("trend") or {}).get("fark")
    if fark is not None and fark >= 0.4:
        rozetler.append("yukseliste")
    if fark is not None and fark <= -0.6:
        rozetler.append("dususte")
    if analiz.get("turist_tuzagi_riski"):
        rozetler.append("turist_tuzagi")
    fp = kriter.get("fiyat_performans")
    if (fp is not None and fp >= 8) or (mekan.get("fiyat_seviyesi") == 1 and g >= 4.3):
        rozetler.append("uygun_fiyat")
    tz = kriter.get("temizlik")
    if tz is not None and tz <= 4:
        rozetler.append("temizlik_sorunu")
    menu = mekan.get("menu") or {}
    if menu.get("durum") == "bulundu" and (menu.get("ay_once") or 0) >= 12:
        rozetler.append("eski_menu")
    return rozetler


# ---------- fiyat ----------
_SEVIYE_TL = {0: 0, 1: 250, 2: 500, 3: 950, 4: 1900}


def kisi_basi_tl(mekan: dict) -> int | None:
    """Sıralama için kişi başı tahmini (TL). Önce Google fiyat aralığı, sonra seviye,
    sonra yorum analizi, en son menü."""
    if mekan.get("fiyat_min") and mekan.get("fiyat_max"):
        return int((mekan["fiyat_min"] + mekan["fiyat_max"]) / 2)
    if mekan.get("fiyat_min"):
        return int(mekan["fiyat_min"])
    if mekan.get("fiyat_seviyesi") is not None:
        return _SEVIYE_TL.get(mekan["fiyat_seviyesi"])
    tahmin = (mekan.get("analiz") or {}).get("kisi_basi_tahmin_tl")
    if tahmin:
        return int(tahmin)
    menu = mekan.get("menu") or {}
    if menu.get("ortalama_fiyat"):
        return int(menu["ortalama_fiyat"])
    return None


def fiyat_etiketi(mekan: dict) -> str:
    if mekan.get("fiyat_min") and mekan.get("fiyat_max"):
        return f"₺{mekan['fiyat_min']}–{mekan['fiyat_max']}"
    if mekan.get("fiyat_min"):
        return f"₺{mekan['fiyat_min']}+"
    seviye = mekan.get("fiyat_seviyesi")
    if seviye:
        return "₺" * seviye
    tahmin = kisi_basi_tl(mekan)
    return f"~₺{tahmin}" if tahmin else ""


def fiyat_seviyesi_tahmin(mekan: dict) -> int | None:
    """Filtre için 1-4 seviye (seviye yoksa TL tahmininden)."""
    if mekan.get("fiyat_seviyesi"):
        return mekan["fiyat_seviyesi"]
    tl = kisi_basi_tl(mekan)
    if tl is None:
        return None
    for seviye, ust in ((1, 350), (2, 700), (3, 1400)):
        if tl <= ust:
            return seviye
    return 4


def puan_rengi(puan: float | None) -> str:
    if puan is None:
        return "yok"
    if puan >= 8:
        return "cok-iyi"
    if puan >= 6.5:
        return "iyi"
    if puan >= 5:
        return "orta"
    return "zayif"


def yuvarla(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, 1)
