"""Mesafe ve açık/kapalı hesapları."""
from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

TURKIYE = ZoneInfo("Europe/Istanbul")
_HAFTA = 7 * 24 * 60


def mesafe_km(lat1, lng1, lat2, lng2) -> float | None:
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def mesafe_yazi(km: float | None) -> str:
    if km is None:
        return ""
    if km < 1:
        return f"{int(round(km * 1000, -1))} m"
    return f"{km:.1f} km".replace(".", ",")


def _dakika(nokta: dict) -> int:
    return nokta.get("day", 0) * 1440 + nokta.get("hour", 0) * 60 + nokta.get("minute", 0)


def acik_mi(periyotlar, an: datetime | None = None) -> bool | None:
    """Google 'periods' listesine göre şu an açık mı? Bilgi yoksa None.

    Google'da gün 0 = Pazar. Kapanışı olmayan tek periyot 7/24 açık demektir.
    """
    if not periyotlar:
        return None
    an = (an or datetime.now(TURKIYE)).astimezone(TURKIYE)
    gun = (an.weekday() + 1) % 7
    simdi = gun * 1440 + an.hour * 60 + an.minute
    for p in periyotlar:
        acilis = p.get("open")
        if not acilis:
            continue
        kapanis = p.get("close")
        if not kapanis:
            return True
        bas, son = _dakika(acilis), _dakika(kapanis)
        if son <= bas:
            son += _HAFTA
        if bas <= simdi < son or bas <= simdi + _HAFTA < son:
            return True
    return False
