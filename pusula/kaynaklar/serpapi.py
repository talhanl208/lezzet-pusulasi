"""SerpApi ile "derin analiz": daha fazla yorum + tarihli menü fotoğrafları.

Google'ın resmi API'si mekan başına 5 yorum veriyor ve fotoğrafların yüklenme tarihini
vermiyor. SerpApi, Google Haritalar'daki "Menü" fotoğraf kategorisini ve her fotoğrafın
tarihini döndürebiliyor. Ücretli bir servis (aylık ücretsiz kotası var); her mekan için
yaklaşık 6-8 arama harcar. Bu yüzden varsayılan olarak sadece istenen mekanlarda çalışır.
"""
from __future__ import annotations

import requests

from ..metin import katla, tarih_coz

URL = "https://serpapi.com/search.json"


class SerpApiHatasi(Exception):
    pass


class SerpApi:
    def __init__(self, api_key: str, oturum: requests.Session | None = None):
        if not api_key:
            raise SerpApiHatasi("SERPAPI_API_KEY tanımlı değil")
        self.api_key = api_key
        self.oturum = oturum or requests.Session()
        self.harcanan = 0

    def _ara(self, **parametreler) -> dict:
        parametreler["api_key"] = self.api_key
        yanit = self.oturum.get(URL, params=parametreler, timeout=60)
        self.harcanan += 1
        try:
            veri = yanit.json()
        except ValueError as e:
            raise SerpApiHatasi(f"SerpApi geçersiz yanıt ({yanit.status_code})") from e
        if yanit.status_code != 200 or veri.get("error"):
            raise SerpApiHatasi(f"SerpApi: {veri.get('error') or yanit.status_code}")
        return veri

    def data_id_bul(self, place_id: str) -> str:
        veri = self._ara(engine="google_maps", place_id=place_id, hl="tr")
        data_id = (veri.get("place_results") or {}).get("data_id")
        if not data_id:
            raise SerpApiHatasi("Mekan SerpApi'de bulunamadı")
        return data_id

    def yorumlar(self, data_id: str, adet: int = 30) -> list[dict]:
        """En yeni yorumlar. İlk sayfa ~8, sonraki sayfalar 20'şer yorum."""
        sonuc, token = [], None
        while len(sonuc) < adet:
            parametre = {"engine": "google_maps_reviews", "data_id": data_id, "hl": "tr",
                         "sort_by": "newestFirst"}
            if token:
                parametre.update(next_page_token=token, num=20)
            veri = self._ara(**parametre)
            for y in veri.get("reviews") or []:
                sonuc.append(yorum_donustur(y))
            token = (veri.get("serpapi_pagination") or {}).get("next_page_token")
            if not token or not veri.get("reviews"):
                break
        return sonuc[:adet]

    def menu_fotolari(self, data_id: str, adet: int = 4) -> list[dict]:
        """Google Haritalar'daki 'Menü' kategorisindeki fotoğraflar, yüklenme tarihleriyle."""
        veri = self._ara(engine="google_maps_photos", data_id=data_id, hl="tr")
        kategori_id = None
        for k in veri.get("categories") or []:
            if katla(k.get("title", "")) in ("menu", "menuler", "menus"):
                kategori_id = k.get("id")
                break
        if not kategori_id:
            return []
        veri = self._ara(engine="google_maps_photos", data_id=data_id, hl="tr",
                         category_id=kategori_id)
        fotolar = []
        for f in (veri.get("photos") or [])[:adet]:
            adres = f.get("image") or f.get("thumbnail")
            if not adres:
                continue
            tarih = self._foto_tarihi(f.get("photo_meta_serpapi_link"))
            fotolar.append({"kaynak": "serpapi", "ref": adres, "kategori": "menu", "menu_mu": 1,
                            "yukleme_tarihi": tarih.isoformat() if tarih else None})
        return fotolar

    def _foto_tarihi(self, baglanti: str | None):
        if not baglanti:
            return None
        try:
            yanit = self.oturum.get(baglanti, params={"api_key": self.api_key}, timeout=60)
            self.harcanan += 1
            veri = yanit.json()
        except (requests.RequestException, ValueError):
            return None
        return tarih_coz(veri.get("date") or (veri.get("user") or {}).get("date"))


def yorum_donustur(y: dict) -> dict:
    kullanici = y.get("user") or {}
    metin = y.get("snippet") or (y.get("extracted_snippet") or {}).get("original") or ""
    tarih = y.get("iso_date") or y.get("iso_date_of_last_edit")
    if not tarih:
        t = tarih_coz(y.get("date"))
        tarih = t.isoformat() if t else None
    try:
        puan = int(round(float(y.get("rating")))) if y.get("rating") is not None else None
    except (TypeError, ValueError):
        puan = None
    return {
        "kaynak": "serpapi",
        "kaynak_id": y.get("review_id"),
        "yazar": kullanici.get("name"),
        "yazar_url": kullanici.get("link"),
        "yazar_foto": kullanici.get("thumbnail"),
        "puan": puan,
        "metin": metin,
        "tarih": tarih,
        "goreli_tarih": y.get("date"),
        "dil": "tr",
    }
