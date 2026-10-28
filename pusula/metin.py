"""Türkçe metin yardımcıları: küçük harf, aksan katlama, slug, göreli tarih."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

_KATLA = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def tr_kucuk(metin: str) -> str:
    """Türkçe kurallarına uygun küçük harf (İ→i, I→ı)."""
    return (metin or "").replace("İ", "i").replace("I", "ı").lower()


def katla(metin: str) -> str:
    """Aramada eşleşme için: küçük harf + aksansız + tek boşluk. 'Köfte' → 'kofte'."""
    sade = tr_kucuk(metin).translate(_KATLA)
    return re.sub(r"\s+", " ", sade).strip()


def slugla(metin: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", katla(metin)).strip("-")


_GORELI = re.compile(
    r"(bir|\d+)\s*(saniye|dakika|saat|gün|gun|hafta|ay|yıl|yil)\s*önce", re.IGNORECASE)
_GUN = {"saniye": 0, "dakika": 0, "saat": 0, "gün": 1, "gun": 1, "hafta": 7, "ay": 30,
        "yıl": 365, "yil": 365}
_GORELI_EN = re.compile(r"(a|an|\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago",
                        re.IGNORECASE)
_GUN_EN = {"second": 0, "minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}


def goreli_tarihten(metin: str, bugun: date | None = None) -> date | None:
    """'3 ay önce', 'bir yıl önce', '2 weeks ago' → yaklaşık tarih."""
    if not metin:
        return None
    bugun = bugun or date.today()
    m = _GORELI.search(tr_kucuk(metin))
    tablo = _GUN
    if not m:
        m = _GORELI_EN.search(metin.lower())
        tablo = _GUN_EN
    if not m:
        return None
    adet = 1 if m.group(1) in ("bir", "a", "an") else int(m.group(1))
    return bugun - timedelta(days=adet * tablo[m.group(2).lower()])


def tarih_coz(deger) -> date | None:
    """ISO tarih/zaman, 'GG-AA-YYYY' veya göreli ifadeyi tarihe çevirir."""
    if not deger:
        return None
    if isinstance(deger, datetime):
        return deger.date()
    if isinstance(deger, date):
        return deger
    metin = str(deger).strip()
    try:
        # Google bazen 9 haneli saniye kesri veriyor; eski Python sürümleri 6 hane kabul eder
        iso = re.sub(r"(\.\d{6})\d+", r"\1", metin.replace("Z", "+00:00"))
        return datetime.fromisoformat(iso).date()
    except ValueError:
        pass
    for kalip in ("%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(metin, kalip).date()
        except ValueError:
            continue
    return goreli_tarihten(metin)


def kac_zaman_once(deger, bugun: date | None = None) -> str:
    """Tarihi '4 ay önce', '1 yıl 2 ay önce', 'bu hafta' gibi okunur hale getirir."""
    t = tarih_coz(deger)
    if not t:
        return ""
    bugun = bugun or date.today()
    gun = (bugun - t).days
    if gun < 0:
        return "yakın zamanda"
    if gun < 7:
        return "bu hafta"
    if gun < 31:
        return f"{gun // 7} hafta önce"
    ay = round(gun / 30.44)
    if ay < 12:
        return f"{ay} ay önce"
    yil, kalan = divmod(ay, 12)
    return f"{yil} yıl {kalan} ay önce" if kalan else f"{yil} yıl önce"


def ay_farki(deger, bugun: date | None = None) -> int | None:
    t = tarih_coz(deger)
    if not t:
        return None
    bugun = bugun or date.today()
    return max(0, round((bugun - t).days / 30.44))


def simdi_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def bin_ayrac(sayi) -> str:
    """12345 → '12.345'"""
    try:
        return f"{int(sayi):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def bulunma(ad: str) -> str:
    """Özel isme bulunma eki: Konya'da, İzmir'de, Muş'ta, Antep'te."""
    if not ad:
        return ""
    kucuk = tr_kucuk(ad)
    unluler = [h for h in kucuk if h in "aıoueiöü"]
    ince = bool(unluler) and unluler[-1] in "eiöü"
    sert = kucuk[-1] in "çfhkpsşt"
    return f"{ad}'{'t' if sert else 'd'}{'e' if ince else 'a'}"
