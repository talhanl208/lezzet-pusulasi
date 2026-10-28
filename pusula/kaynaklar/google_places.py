"""Google Places API (New) istemcisi.

Resmi API kullanılır (Google Haritalar sayfasını kazımak kullanım şartlarına aykırı ve
kısa sürede engellenir). Maliyeti düşürmek için yorumlar ve fotoğraflar ayrı ayrı
'Place Details' çağrısıyla değil, doğrudan Text Search yanıtında istenir: tek istekte
20 mekan gelir.

Not: API mekan başına en fazla 5 yorum ve 10 fotoğraf döndürür. Daha fazlası için
SerpApi tabanlı "derin analiz" kullanılabilir (bkz. serpapi.py).
"""
from __future__ import annotations

import time

import requests

from ..kategori import kategori_belirle

TABAN = "https://places.googleapis.com/v1"

ALAN_MASKESI = ",".join(f"places.{a}" for a in [
    "id", "displayName", "formattedAddress", "shortFormattedAddress", "addressComponents",
    "location", "rating", "userRatingCount", "priceLevel", "priceRange", "types",
    "primaryType", "primaryTypeDisplayName", "googleMapsUri", "websiteUri",
    "nationalPhoneNumber", "regularOpeningHours", "businessStatus", "reviews",
    "reviewSummary", "photos", "servesVegetarianFood", "takeout", "delivery", "dineIn",
    "outdoorSeating", "goodForChildren", "goodForGroups", "reservable", "servesBeer",
    "servesWine", "servesCocktails", "servesBreakfast", "allowsDogs", "liveMusic",
    "parkingOptions",
]) + ",nextPageToken"

_FIYAT = {"PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2,
          "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4}


class GooglePlacesHatasi(Exception):
    pass


class GunlukSinirHatasi(GooglePlacesHatasi):
    """Uygulamanın kendi günlük istek sınırı doldu (fatura güvenliği)."""


class GooglePlaces:
    def __init__(self, api_key: str, oturum: requests.Session | None = None, dil: str = "tr",
                 sinir=None):
        """sinir: sinir("arama"|"foto") → bool. False dönerse istek hiç gönderilmez."""
        if not api_key:
            raise GooglePlacesHatasi("GOOGLE_PLACES_API_KEY tanımlı değil")
        self.api_key = api_key
        self.oturum = oturum or requests.Session()
        self.dil = dil
        self.sinir = sinir

    def _sinir_kontrol(self, tur: str) -> None:
        if self.sinir and not self.sinir(tur):
            raise GunlukSinirHatasi(
                f"Bugünkü Google {tur} sınırı doldu (.env'deki GUNLUK_{tur.upper()}_LIMITI). "
                "Sayaç gece yarısı sıfırlanır.")

    def _istek(self, yontem: str, url: str, **kw) -> dict:
        basliklar = kw.pop("headers", {})
        basliklar["X-Goog-Api-Key"] = self.api_key
        for deneme in range(3):
            yanit = self.oturum.request(yontem, url, headers=basliklar, timeout=30, **kw)
            if yanit.status_code == 429 and deneme < 2:
                time.sleep(2 * (deneme + 1))
                continue
            if yanit.status_code != 200:
                try:
                    mesaj = yanit.json().get("error", {}).get("message", yanit.text)
                except ValueError:
                    mesaj = yanit.text
                raise GooglePlacesHatasi(f"Google Places {yanit.status_code}: {mesaj[:300]}")
            return yanit.json()
        raise GooglePlacesHatasi("Google Places istek sınırı aşıldı (429)")

    def metin_ara(self, sorgu: str, lat: float, lng: float, yaricap_m: float,
                  sayfa_token: str | None = None) -> tuple[list[dict], str | None]:
        govde = {
            "textQuery": sorgu,
            "languageCode": self.dil,
            "regionCode": "TR",
            "pageSize": 20,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng},
                                        "radius": float(min(yaricap_m, 50000))}},
        }
        if sayfa_token:
            govde["pageToken"] = sayfa_token
        self._sinir_kontrol("arama")
        veri = self._istek("POST", f"{TABAN}/places:searchText", json=govde,
                           headers={"X-Goog-FieldMask": ALAN_MASKESI})
        return veri.get("places", []), veri.get("nextPageToken")

    def foto_uri(self, foto_adi: str, en_fazla_px: int = 900) -> str:
        """Fotoğrafın geçici, herkese açık adresini döndürür (API anahtarı içermez)."""
        self._sinir_kontrol("foto")
        veri = self._istek("GET", f"{TABAN}/{foto_adi}/media",
                           params={"maxWidthPx": en_fazla_px, "skipHttpRedirect": "true"})
        uri = veri.get("photoUri")
        if not uri:
            raise GooglePlacesHatasi("Fotoğraf adresi alınamadı")
        return uri


def _metin(d) -> str:
    if isinstance(d, dict):
        return d.get("text") or ""
    return d or ""


def _ilce(bilesenler) -> str:
    for tur in ("administrative_area_level_2", "sublocality_level_1", "locality"):
        for b in bilesenler or []:
            if tur in (b.get("types") or []):
                return b.get("longText") or b.get("shortText") or ""
    return ""


def _fiyat_araligi(aralik) -> tuple[int | None, int | None]:
    if not aralik:
        return None, None

    def tl(p):
        try:
            return int(float(p.get("units", 0))) if p else None
        except (TypeError, ValueError):
            return None
    return tl(aralik.get("startPrice")), tl(aralik.get("endPrice"))


def donustur(p: dict) -> dict:
    """Places API yanıtındaki bir mekanı uygulamanın kayıt biçimine çevirir."""
    turler = p.get("types") or []
    fiyat_min, fiyat_max = _fiyat_araligi(p.get("priceRange"))
    fiyat_seviyesi = _FIYAT.get(p.get("priceLevel"))
    ad = _metin(p.get("displayName"))
    saatler = p.get("regularOpeningHours") or {}
    ozet = p.get("reviewSummary") or {}
    yorumlar = []
    for y in p.get("reviews") or []:
        metin = _metin(y.get("originalText")) or _metin(y.get("text"))
        yazar = y.get("authorAttribution") or {}
        yorumlar.append({
            "kaynak": "google",
            "kaynak_id": y.get("name"),
            "yazar": yazar.get("displayName"),
            "yazar_url": yazar.get("uri"),
            "yazar_foto": yazar.get("photoUri"),
            "puan": y.get("rating"),
            "metin": metin,
            "tarih": y.get("publishTime"),
            "goreli_tarih": y.get("relativePublishTimeDescription"),
            "dil": (y.get("originalText") or y.get("text") or {}).get("languageCode"),
        })
    fotolar = []
    for i, f in enumerate(p.get("photos") or []):
        yazar = (f.get("authorAttributions") or [{}])[0]
        fotolar.append({"kaynak": "google", "ref": f.get("name"), "genislik": f.get("widthPx"),
                        "yukseklik": f.get("heightPx"), "yazar": yazar.get("displayName"),
                        "yazar_url": yazar.get("uri"), "sira": i})
    park = p.get("parkingOptions") or {}
    return {
        "place_id": p.get("id"),
        "ad": ad,
        "adres": p.get("shortFormattedAddress") or p.get("formattedAddress"),
        "ilce": _ilce(p.get("addressComponents")),
        "lat": (p.get("location") or {}).get("latitude"),
        "lng": (p.get("location") or {}).get("longitude"),
        "google_puan": p.get("rating"),
        "yorum_sayisi": p.get("userRatingCount") or 0,
        "fiyat_seviyesi": fiyat_seviyesi,
        "fiyat_min": fiyat_min,
        "fiyat_max": fiyat_max,
        "turler": turler,
        "birincil_tur": p.get("primaryType") or "",
        "birincil_tur_adi": _metin(p.get("primaryTypeDisplayName")),
        "kategori": kategori_belirle(ad, turler, p.get("primaryType") or "", fiyat_seviyesi),
        "telefon": p.get("nationalPhoneNumber"),
        "web": p.get("websiteUri"),
        "maps_url": p.get("googleMapsUri"),
        "calisma_saatleri": saatler.get("weekdayDescriptions") or [],
        "saat_periyotlari": saatler.get("periods") or [],
        "isletme_durumu": p.get("businessStatus"),
        "google_ozet": _metin(ozet.get("text")),
        "google_ozet_aciklama": _metin(ozet.get("disclosureText")),
        "ozellikler": {
            "vejetaryen": p.get("servesVegetarianFood"),
            "paket": p.get("takeout"),
            "teslimat": p.get("delivery"),
            "acik_alan": p.get("outdoorSeating"),
            "cocuk": p.get("goodForChildren"),
            "grup": p.get("goodForGroups"),
            "rezervasyon": p.get("reservable"),
            "alkol": any(p.get(k) for k in ("servesBeer", "servesWine", "servesCocktails")) or None,
            "kahvalti": p.get("servesBreakfast"),
            "evcil": p.get("allowsDogs"),
            "canli_muzik": p.get("liveMusic"),
            "otopark": any(park.values()) if park else None,
        },
        "yorumlar": yorumlar,
        "fotolar": fotolar,
    }
