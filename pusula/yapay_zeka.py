"""Claude API ile yorum analizi ve menü fotoğrafı okuma.

SDK yerine doğrudan HTTP kullanılır; tek bağımlılık `requests`.
Yanıtı yapılandırılmış almak için Claude'a bir "araç" tanımlanır ve kullanması zorunlu
tutulur (tool_choice). Böylece çıktı her zaman beklenen JSON şemasında gelir.
"""
from __future__ import annotations

import logging
import time

import requests

from .puanlama import KRITERLER

log = logging.getLogger(__name__)
API_URL = "https://api.anthropic.com/v1/messages"
API_SURUMU = "2023-06-01"


class YapayZekaHatasi(Exception):
    pass


class Claude:
    def __init__(self, api_key: str, model: str, oturum: requests.Session | None = None,
                 zaman_asimi: int = 90):
        self.api_key = api_key
        self.model = model
        self.oturum = oturum or requests.Session()
        self.zaman_asimi = zaman_asimi

    def arac_cagir(self, sistem: str, icerik, arac: dict, max_tokens: int = 1500) -> dict:
        govde = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": sistem,
            "tools": [arac],
            "tool_choice": {"type": "tool", "name": arac["name"]},
            "messages": [{"role": "user", "content": icerik}],
        }
        basliklar = {"x-api-key": self.api_key, "anthropic-version": API_SURUMU,
                     "content-type": "application/json"}
        son_hata = None
        for deneme in range(4):
            try:
                yanit = self.oturum.post(API_URL, json=govde, headers=basliklar,
                                         timeout=self.zaman_asimi)
            except requests.RequestException as e:
                son_hata = str(e)
                time.sleep(2 ** deneme)
                continue
            if yanit.status_code in (429, 500, 502, 503, 529):
                son_hata = f"HTTP {yanit.status_code}"
                time.sleep(float(yanit.headers.get("retry-after", 2 ** (deneme + 1))))
                continue
            if yanit.status_code != 200:
                raise YapayZekaHatasi(f"Claude API {yanit.status_code}: {yanit.text[:300]}")
            for blok in yanit.json().get("content", []):
                if blok.get("type") == "tool_use" and blok.get("name") == arac["name"]:
                    return blok.get("input") or {}
            raise YapayZekaHatasi("Claude yanıtında beklenen araç çağrısı yok")
        raise YapayZekaHatasi(f"Claude API'ye ulaşılamadı ({son_hata})")


# ---------------- yorum analizi ----------------
_KRITER_SEMASI = {k: {"type": ["integer", "null"], "minimum": 1, "maximum": 10,
                      "description": f"{ad} puanı (1-10). Yorumlarda kanıt yoksa null."}
                  for k, ad in KRITERLER.items()}

ANALIZ_ARACI = {
    "name": "analiz_kaydet",
    "description": "Bir restoranın yorum analizini yapılandırılmış olarak kaydeder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ozet": {"type": "string", "description": "1-2 cümlelik dengeli Türkçe özet."},
            "artilar": {"type": "array", "items": {"type": "string"}, "maxItems": 5,
                        "description": "Yorumlarda tekrar eden güçlü yönler, kısa cümleler."},
            "eksiler": {"type": "array", "items": {"type": "string"}, "maxItems": 5,
                        "description": "Yorumlarda tekrar eden zayıf yönler. Yoksa boş liste."},
            "kriterler": {"type": "object", "properties": _KRITER_SEMASI,
                          "required": list(KRITERLER)},
            "one_cikan_lezzetler": {"type": "array", "items": {"type": "string"},
                                    "maxItems": 6, "description": "Övülen yemek adları."},
            "uyarilar": {"type": "array", "items": {"type": "string"}, "maxItems": 3,
                         "description": "Gitmeden bilinmesi gereken pratik notlar "
                                        "(nakit, rezervasyon, park, sıra vb.)."},
            "turist_tuzagi_riski": {"type": "boolean",
                                    "description": "Fahiş fiyat, hesap şişirme, fiyatsız menü "
                                                   "gibi şikayetler birden fazla yorumda varsa true."},
            "kimlere_uygun": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "kisi_basi_tahmin_tl": {"type": ["integer", "null"],
                                    "description": "Yorumlarda geçen fiyatlardan kişi başı TL "
                                                   "tahmini; bilgi yoksa null."},
        },
        "required": ["ozet", "artilar", "eksiler", "kriterler", "one_cikan_lezzetler",
                     "uyarilar", "turist_tuzagi_riski", "kimlere_uygun", "kisi_basi_tahmin_tl"],
    },
}

ANALIZ_SISTEMI = (
    "Türkiye'de seyahat eden birine restoran seçiminde yardım eden tarafsız bir yemek "
    "editörüsün. Sana bir mekanın Google bilgileri ve yorumları verilecek. Sadece "
    "yorumlarda gerçekten geçen bilgilere dayan; tahmin yürütme, abartma. Tek bir yorumda "
    "geçen şeyi genel kural gibi sunma; birden fazla yorumda tekrar edenleri öne çıkar. "
    "Kısa, sade Türkçe kullan. Kriter puanlarında 5 ortalama, 8+ gerçekten övülen, 3- ciddi "
    "şikayet edilen anlamına gelir. analiz_kaydet aracını kullanarak yanıt ver."
)


def _yorum_metni(mekan: dict, yorumlar: list[dict]) -> str:
    satirlar = [
        f"Mekan: {mekan.get('ad')}",
        f"Tür: {mekan.get('birincil_tur_adi') or mekan.get('kategori')}",
        f"Adres: {mekan.get('adres') or '-'}",
        f"Google puanı: {mekan.get('google_puan')} ({mekan.get('yorum_sayisi')} değerlendirme)",
    ]
    if mekan.get("fiyat_min"):
        satirlar.append(f"Google fiyat aralığı: {mekan.get('fiyat_min')}-{mekan.get('fiyat_max')} TL")
    if mekan.get("google_ozet"):
        satirlar.append(f"Google'ın yorum özeti: {mekan['google_ozet']}")
    satirlar.append("\nYorumlar (en yeniden eskiye):")
    for i, y in enumerate(yorumlar[:40], 1):
        tarih = (y.get("tarih") or "")[:10] or y.get("goreli_tarih") or "tarih yok"
        metin = (y.get("metin") or "").strip().replace("\n", " ")[:900]
        satirlar.append(f"{i}. [{y.get('puan') or '?'}★, {tarih}] {metin or '(yorumsuz puan)'}")
    return "\n".join(satirlar)


def _liste(deger, en_fazla: int) -> list[str]:
    if not isinstance(deger, list):
        return []
    return [str(x).strip()[:160] for x in deger if str(x).strip()][:en_fazla]


def analizi_temizle(ham: dict, yorum_adedi: int) -> dict:
    """Modelden geleni doğrular; şema dışı değerleri düzeltir."""
    kriterler = {}
    for k in KRITERLER:
        d = (ham.get("kriterler") or {}).get(k)
        try:
            kriterler[k] = None if d is None else max(1, min(10, int(round(float(d)))))
        except (TypeError, ValueError):
            kriterler[k] = None
    kisi = ham.get("kisi_basi_tahmin_tl")
    try:
        kisi = int(kisi) if kisi not in (None, "") else None
    except (TypeError, ValueError):
        kisi = None
    return {
        "yontem": "claude",
        "ozet": str(ham.get("ozet") or "").strip()[:500],
        "artilar": _liste(ham.get("artilar"), 5),
        "eksiler": _liste(ham.get("eksiler"), 5),
        "kriterler": kriterler,
        "one_cikan_lezzetler": _liste(ham.get("one_cikan_lezzetler"), 6),
        "uyarilar": _liste(ham.get("uyarilar"), 3),
        "turist_tuzagi_riski": bool(ham.get("turist_tuzagi_riski")),
        "kimlere_uygun": _liste(ham.get("kimlere_uygun"), 4),
        "kisi_basi_tahmin_tl": kisi,
        "yorum_adedi": yorum_adedi,
    }


def yorumlari_analiz_et(claude: Claude, mekan: dict, yorumlar: list[dict]) -> dict:
    ham = claude.arac_cagir(ANALIZ_SISTEMI, _yorum_metni(mekan, yorumlar), ANALIZ_ARACI)
    return analizi_temizle(ham, len(yorumlar))


# ---------------- menü okuma ----------------
MENU_ARACI = {
    "name": "menu_kaydet",
    "description": "Fotoğraflardan hangilerinin menü olduğunu ve menüdeki ürünleri kaydeder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "menu_fotolari": {"type": "array", "items": {"type": "integer"},
                              "description": "Menü, fiyat listesi veya menü tahtası gösteren "
                                             "fotoğrafların numaraları. Yemek tabağı menü sayılmaz."},
            "urunler": {
                "type": "array", "maxItems": 60,
                "items": {"type": "object", "properties": {
                    "ad": {"type": "string"},
                    "fiyat": {"type": ["number", "null"]},
                    "kategori": {"type": "string",
                                 "description": "çorba, ana yemek, kebap, pide, tatlı, içecek, "
                                                "kahvaltı, meze, salata, diğer"},
                }, "required": ["ad", "fiyat", "kategori"]},
            },
            "para_birimi": {"type": "string", "description": "Genelde TRY."},
            "not": {"type": "string", "description": "Okunabilirlik veya eksik kısım notu."},
        },
        "required": ["menu_fotolari", "urunler", "para_birimi", "not"],
    },
}

MENU_SISTEMI = (
    "Restoran fotoğraflarını inceleyen dikkatli bir asistansın. Görevin menü/fiyat listesi "
    "olan fotoğrafları bulmak ve okunabilen ürünleri fiyatlarıyla çıkarmak. Okuyamadığın "
    "fiyatı uydurma, null bırak. menu_kaydet aracını kullan."
)


def menu_oku(claude: Claude, foto_urller: list[str], hepsi_menu: bool = False) -> dict:
    """foto_urller: herkese açık görsel adresleri. hepsi_menu=True ise sınıflandırma atlanır."""
    icerik = []
    for i, url in enumerate(foto_urller, 1):
        icerik.append({"type": "text", "text": f"Fotoğraf {i}:"})
        icerik.append({"type": "image", "source": {"type": "url", "url": url}})
    talimat = ("Bu fotoğrafların hepsi menü fotoğrafı. Ürünleri ve fiyatları çıkar."
               if hepsi_menu else
               "Hangi fotoğraflar menü? Menü olanlardan ürünleri ve fiyatları çıkar. "
               "Hiçbiri menü değilse menu_fotolari ve urunler boş liste olsun.")
    icerik.append({"type": "text", "text": talimat})
    ham = claude.arac_cagir(MENU_SISTEMI, icerik, MENU_ARACI, max_tokens=3000)
    numaralar = sorted({int(n) for n in ham.get("menu_fotolari") or []
                        if str(n).isdigit() and 1 <= int(n) <= len(foto_urller)})
    if hepsi_menu:
        numaralar = list(range(1, len(foto_urller) + 1))
    urunler = []
    for u in ham.get("urunler") or []:
        ad = str(u.get("ad") or "").strip()
        if not ad:
            continue
        try:
            fiyat = None if u.get("fiyat") in (None, "") else float(u["fiyat"])
        except (TypeError, ValueError):
            fiyat = None
        urunler.append({"ad": ad[:80], "fiyat": fiyat,
                        "kategori": str(u.get("kategori") or "diğer")[:20]})
    return {"menu_fotolari": numaralar, "urunler": urunler,
            "para_birimi": ham.get("para_birimi") or "TRY", "not": ham.get("not") or ""}
