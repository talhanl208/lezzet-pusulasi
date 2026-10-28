"""Şehir listesindeki filtreleme, sıralama ve mekan bilgisini zenginleştirme."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from .kategori import kategori_adi
from .konum import acik_mi, mesafe_km
from .metin import katla
from .puanlama import (fiyat_etiketi, fiyat_seviyesi_tahmin, kisi_basi_tl, pusula_puani,
                       rozet_belirle)
from .tarama import menu_zenginlestir

OZELLIKLER = {
    "vejetaryen": "Vejetaryen seçenek", "paket": "Paket servis", "teslimat": "Eve teslimat",
    "acik_alan": "Açık alan", "cocuk": "Çocuk dostu", "rezervasyon": "Rezervasyon",
    "alkol": "Alkol servisi", "kahvalti": "Kahvaltı", "otopark": "Otopark",
}
SIRALAMALAR = {
    "pusula": "Pusula Puanı", "google": "Google puanı", "yorum": "Yorum sayısı",
    "fiyat_artan": "Önce ucuz", "fiyat_azalan": "Önce pahalı", "mesafe": "Önce yakın",
}


@dataclass
class Filtre:
    q: str = ""
    kategoriler: list = field(default_factory=list)
    fiyatlar: list = field(default_factory=list)
    min_google: float | None = None
    min_puan: float | None = None
    min_yorum: int | None = None
    acik: bool = False
    ozellikler: list = field(default_factory=list)
    ilce: str = ""
    max_km: float | None = None
    rozetler: list = field(default_factory=list)
    sirala: str = "pusula"
    n: int = 50
    lat: float | None = None
    lng: float | None = None
    ref: str = "merkez"

    def aktif_sayisi(self) -> int:
        return sum(bool(x) for x in (self.q, self.kategoriler, self.fiyatlar, self.min_google,
                                     self.min_puan, self.min_yorum, self.acik, self.ozellikler,
                                     self.ilce, self.max_km, self.rozetler))


def _sayi(deger, tur=float):
    try:
        return tur(str(deger).replace(",", ".")) if deger not in (None, "") else None
    except ValueError:
        return None


def filtre_oku(args, varsayilan_n: int = 50) -> Filtre:
    f = Filtre()
    f.q = (args.get("q") or "").strip()[:80]
    f.kategoriler = args.getlist("kat")
    f.fiyatlar = [int(x) for x in args.getlist("fiyat") if x.isdigit()]
    f.min_google = _sayi(args.get("min_g"))
    f.min_puan = _sayi(args.get("min_p"))
    f.min_yorum = _sayi(args.get("min_yorum"), int)
    f.acik = args.get("acik") == "1"
    f.ozellikler = [o for o in args.getlist("oz") if o in OZELLIKLER]
    f.ilce = (args.get("ilce") or "").strip()
    f.max_km = _sayi(args.get("max_km"))
    f.rozetler = args.getlist("rozet")
    f.sirala = args.get("sirala") if args.get("sirala") in SIRALAMALAR else "pusula"
    f.n = max(10, min(500, _sayi(args.get("n"), int) or varsayilan_n))
    f.lat, f.lng = _sayi(args.get("lat")), _sayi(args.get("lng"))
    f.ref = args.get("ref") if args.get("ref") in ("konum", "nokta") and f.lat and f.lng else "merkez"
    return f


def zenginlestir(mekanlar: list[dict], yorumlar: dict, kapaklar: dict, sehir: dict,
                 agirlik: dict, google_payi: int, ref: tuple | None = None) -> list[dict]:
    puanlar = [m["google_puan"] for m in mekanlar if m.get("google_puan")]
    ort = statistics.mean(puanlar) if puanlar else 4.2
    ref = ref or (sehir["lat"], sehir["lng"])
    for m in mekanlar:
        y = yorumlar.get(m["id"], [])
        m["menu"] = menu_zenginlestir(m.get("menu"))
        m["puan"] = pusula_puani(m, y, ort, agirlik, google_payi)
        m["rozetler"] = rozet_belirle(m, m["puan"])
        m["kisi_basi"] = kisi_basi_tl(m)
        m["fiyat_etiketi"] = fiyat_etiketi(m)
        m["fiyat_sev"] = fiyat_seviyesi_tahmin(m)
        m["acik"] = acik_mi(m.get("saat_periyotlari"))
        m["mesafe"] = mesafe_km(ref[0], ref[1], m.get("lat"), m.get("lng"))
        m["kapak"] = kapaklar.get(m["id"])
        m["yorum_adedi"] = len(y)
        analiz = m.get("analiz") or {}
        parcalar = [m["ad"], m.get("ilce") or "", kategori_adi(m.get("kategori")),
                    m.get("birincil_tur_adi") or "", " ".join(analiz.get("one_cikan_lezzetler") or []),
                    " ".join(u.get("ad", "") for u in (m["menu"] or {}).get("urunler") or []),
                    " ".join((x.get("metin") or "") for x in y)]
        m["_arama"] = " " + katla(" ".join(parcalar)) + " "
    return mekanlar


def uygula(mekanlar: list[dict], f: Filtre) -> list[dict]:
    terimler = katla(f.q).split()
    sonuc = []
    for m in mekanlar:
        if terimler and not all(t in m["_arama"] for t in terimler):
            continue
        if f.kategoriler and m.get("kategori") not in f.kategoriler:
            continue
        if f.fiyatlar and m.get("fiyat_sev") not in f.fiyatlar:
            continue
        if f.min_google and (m.get("google_puan") or 0) < f.min_google:
            continue
        if f.min_puan and (m["puan"].get("puan") or 0) < f.min_puan:
            continue
        if f.min_yorum and (m.get("yorum_sayisi") or 0) < f.min_yorum:
            continue
        if f.acik and m.get("acik") is not True:
            continue
        if f.ozellikler and not all((m.get("ozellikler") or {}).get(o) for o in f.ozellikler):
            continue
        if f.ilce and m.get("ilce") != f.ilce:
            continue
        if f.max_km and (m.get("mesafe") is None or m["mesafe"] > f.max_km):
            continue
        if f.rozetler and not set(f.rozetler) & set(m.get("rozetler") or []):
            continue
        sonuc.append(m)
    return sirala(sonuc, f.sirala)


def sirala(mekanlar: list[dict], anahtar: str) -> list[dict]:
    yok = float("inf")
    anahtarlar = {
        "pusula": lambda m: (-(m["puan"].get("puan") or -1), -(m.get("yorum_sayisi") or 0)),
        "google": lambda m: (-(m.get("google_puan") or 0), -(m.get("yorum_sayisi") or 0)),
        "yorum": lambda m: -(m.get("yorum_sayisi") or 0),
        "fiyat_artan": lambda m: (m["kisi_basi"] if m.get("kisi_basi") is not None else yok,
                                  -(m["puan"].get("puan") or 0)),
        "fiyat_azalan": lambda m: (-(m["kisi_basi"] or -1), -(m["puan"].get("puan") or 0)),
        "mesafe": lambda m: m["mesafe"] if m.get("mesafe") is not None else yok,
    }
    return sorted(mekanlar, key=anahtarlar.get(anahtar, anahtarlar["pusula"]))


def rota_sirala(mekanlar: list[dict]) -> list[dict]:
    """Gezi listesi için en yakın komşu sırası: her seferinde en yakın sonraki durak."""
    if len(mekanlar) < 3:
        return mekanlar
    kalan = list(mekanlar[1:])
    rota = [mekanlar[0]]
    while kalan:
        son = rota[-1]
        en_yakin = min(kalan, key=lambda m: mesafe_km(son["lat"], son["lng"], m["lat"], m["lng"])
                       or 0)
        rota.append(en_yakin)
        kalan.remove(en_yakin)
    return rota


def rota_uzunlugu(mekanlar: list[dict]) -> float:
    toplam = 0.0
    for a, b in zip(mekanlar, mekanlar[1:]):
        toplam += mesafe_km(a["lat"], a["lng"], b["lat"], b["lng"]) or 0
    return toplam
