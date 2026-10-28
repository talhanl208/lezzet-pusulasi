"""Şehir tarama akışı: veri çek → kaydet → yorumları analiz et → menü bul → puanla."""
from __future__ import annotations

import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import analiz_kural
from .db import Depo
from .kategori import yemek_mekani_mi
from .konum import mesafe_km
from .metin import ay_farki, simdi_iso
from .puanlama import pusula_puani
from .yapay_zeka import Claude, YapayZekaHatasi, menu_oku, yorumlari_analiz_et

log = logging.getLogger(__name__)

SORGULAR = ["restoran", "en iyi restoranlar", "lokanta", "kebapçı", "kafe", "kahvaltı",
            "fast food", "balık restoranı", "pide lahmacun", "tatlıcı", "dönerci", "meyhane"]
MAKS_GOOGLE_ISTEGI = 12
ANA_YEMEK = {"ana yemek", "kebap", "pide", "kahvaltı"}


def _claude(cfg) -> Claude | None:
    if cfg.get("ANTHROPIC_API_KEY"):
        return Claude(cfg["ANTHROPIC_API_KEY"], cfg["CLAUDE_MODEL"])
    return None


def google_istemcisi(cfg, depo: Depo):
    """Günlük istek sayacına bağlı Google Places istemcisi."""
    from .kaynaklar.google_places import GooglePlaces
    limitler = {"arama": int(cfg.get("GUNLUK_ARAMA_LIMITI", 200)),
                "foto": int(cfg.get("GUNLUK_FOTO_LIMITI", 300))}
    return GooglePlaces(cfg["GOOGLE_PLACES_API_KEY"],
                        sinir=lambda tur: depo.sayac_artir(f"google_{tur}", limitler[tur]))


def menu_zenginlestir(menu: dict | None) -> dict | None:
    """Kayıtlı menüye 'kaç ay önce' ve ortalama fiyat bilgisini ekler."""
    if not menu:
        return menu
    menu = dict(menu)
    menu["ay_once"] = ay_farki(menu.get("en_yeni_tarih"))
    fiyatlar = [u["fiyat"] for u in menu.get("urunler") or []
                if u.get("fiyat") and u.get("kategori") in ANA_YEMEK]
    if not fiyatlar:
        fiyatlar = [u["fiyat"] for u in menu.get("urunler") or [] if u.get("fiyat")]
    menu["ortalama_fiyat"] = int(statistics.median(fiyatlar)) if fiyatlar else None
    return menu


# ---------------------------------------------------------------- veri toplama
def _google_topla(cfg, depo: Depo, il: dict, hedef: int, bolge: str, ilerleme) -> list[dict]:
    from .kaynaklar.google_places import GunlukSinirHatasi, donustur

    gp = google_istemcisi(cfg, depo)
    yaricap_m = il["yaricap_km"] * 1000
    adaylar: dict[str, dict] = {}
    bekleyen_sayfalar: list[tuple[str, str]] = []
    istek = 0
    yer = f"{bolge} {il['ad']}" if bolge else il["ad"]

    def isle(ham_liste):
        for ham in ham_liste:
            kayit = donustur(ham)
            if not kayit["place_id"] or kayit["place_id"] in adaylar:
                continue
            if kayit.get("isletme_durumu") == "CLOSED_PERMANENTLY":
                continue
            if not yemek_mekani_mi(kayit["turler"]) or not kayit.get("google_puan"):
                continue
            if (kayit.get("yorum_sayisi") or 0) < 5:
                continue
            uzaklik = mesafe_km(il["lat"], il["lng"], kayit["lat"], kayit["lng"])
            if not bolge and uzaklik is not None and uzaklik > il["yaricap_km"] * 1.6:
                continue
            adaylar[kayit["place_id"]] = kayit

    try:
        for sorgu in SORGULAR:
            if len(adaylar) >= hedef * 1.4 or istek >= MAKS_GOOGLE_ISTEGI:
                break
            ilerleme(5 + 30 * len(adaylar) / (hedef * 1.4), f"Google'da aranıyor: “{yer} {sorgu}”")
            sonuc, token = gp.metin_ara(f"{yer} {sorgu}", il["lat"], il["lng"], yaricap_m)
            istek += 1
            isle(sonuc)
            if token:
                bekleyen_sayfalar.append((f"{yer} {sorgu}", token))
        while len(adaylar) < hedef and bekleyen_sayfalar and istek < MAKS_GOOGLE_ISTEGI:
            sorgu, token = bekleyen_sayfalar.pop(0)
            sonuc, yeni_token = gp.metin_ara(sorgu, il["lat"], il["lng"], yaricap_m, token)
            istek += 1
            isle(sonuc)
            if yeni_token:
                bekleyen_sayfalar.append((sorgu, yeni_token))
    except GunlukSinirHatasi as e:
        if not adaylar:
            raise
        ilerleme(35, f"{e} Bulunan {len(adaylar)} mekanla devam ediliyor.")
    ilerleme(35, f"{len(adaylar)} mekan bulundu ({istek} Google isteği)")
    return list(adaylar.values())


def sehir_tara(cfg, depo: Depo, ilerleme, il: dict, hedef: int = 50, bolge: str = "") -> str:
    sehir = depo.sehir_kaydet(il)
    demo = cfg.get("DEMO")
    if demo:
        from .kaynaklar.demo import sehir_mekanlari
        ilerleme(10, "Demo verisi hazırlanıyor (API anahtarı tanımlı değil)")
        kayitlar = sehir_mekanlari(il)
    else:
        kayitlar = _google_topla(cfg, depo, il, hedef, bolge, ilerleme)
    if not kayitlar:
        raise RuntimeError("Bu şehirde uygun mekan bulunamadı.")

    kaynak = "demo" if demo else "google"
    mekan_idler = []
    for i, kayit in enumerate(kayitlar):
        mekan_id = depo.mekan_kaydet(sehir["id"], kaynak, kayit)
        mekan_idler.append(mekan_id)
        if kayit.get("demo_menu"):
            depo.menu_kaydet(mekan_id, kayit["demo_menu"])
        if i % 10 == 0:
            ilerleme(35 + 10 * i / len(kayitlar), f"Kaydediliyor: {kayit['ad']}")

    analizleri_yap(cfg, depo, mekan_idler, ilerleme, baslangic=45, bitis=85,
                   claude_kullan=cfg.get("CLAUDE_TOPLU_ANALIZ", True))
    puanlari_guncelle(depo, sehir["id"])

    # Thread'siz sunucuda (PythonAnywhere) menü taraması mekan sayfasından tek tek yapılır
    limit = int(cfg.get("MENU_TARAMA_LIMITI", 0)) if cfg.get("ARKA_PLAN_ISLERI", True) else 0
    if not demo and limit and _claude(cfg):
        eniyiler = _en_iyiler(depo, sehir["id"], limit)
        for i, mekan_id in enumerate(eniyiler):
            ilerleme(85 + 10 * i / max(1, len(eniyiler)), "Fotoğraflarda menü aranıyor")
            try:
                menu_tara(cfg, depo, lambda *_: None, mekan_id)
            except Exception as e:  # tek mekanın hatası taramayı durdurmasın
                log.warning("Menü taraması başarısız (%s): %s", mekan_id, e)

    derin = int(cfg.get("DERIN_ANALIZ_LIMITI", 0)) if cfg.get("ARKA_PLAN_ISLERI", True) else 0
    if not demo and derin and cfg.get("SERPAPI_API_KEY"):
        for mekan_id in _en_iyiler(depo, sehir["id"], derin):
            ilerleme(96, "Derin analiz yapılıyor")
            try:
                derin_analiz(cfg, depo, lambda *_: None, mekan_id)
            except Exception as e:
                log.warning("Derin analiz başarısız (%s): %s", mekan_id, e)

    puanlari_guncelle(depo, sehir["id"])
    depo.sehir_tarandi(sehir["id"], kaynak)
    ilerleme(100, f"{len(mekan_idler)} mekan hazır")
    return f"/sehir/{sehir['slug']}"


def _en_iyiler(depo: Depo, sehir_id: int, adet: int) -> list[int]:
    mekanlar = depo.sehir_mekanlari(sehir_id)
    mekanlar.sort(key=lambda m: -(m.get("pusula_puani") or 0))
    return [m["id"] for m in mekanlar[:adet]]


# ---------------------------------------------------------------- analiz
def analizleri_yap(cfg, depo: Depo, mekan_idler: list[int], ilerleme, baslangic=0, bitis=100,
                   claude_kullan: bool = True):
    claude = _claude(cfg) if claude_kullan else None
    isler = [(depo.mekan(i), depo.yorumlar(i)) for i in mekan_idler]
    toplam = max(1, len(isler))

    def tek(mekan, yorumlar):
        if claude and yorumlar:
            try:
                return yorumlari_analiz_et(claude, mekan, yorumlar)
            except YapayZekaHatasi as e:
                log.warning("Claude analizi başarısız, kurala dönülüyor: %s", e)
        return analiz_kural.analiz_et(mekan, yorumlar)

    biten = 0

    def kaydet(mekan, analiz):
        nonlocal biten
        analiz["tarih"] = simdi_iso()
        depo.analiz_kaydet(mekan["id"], analiz)
        biten += 1
        if biten % 5 == 0 or biten == toplam:
            yontem = "Claude" if analiz["yontem"] == "claude" else "kural tabanlı analiz"
            ilerleme(baslangic + (bitis - baslangic) * biten / toplam,
                     f"Yorumlar okunuyor ({yontem}): {biten}/{toplam}")

    # Thread desteklemeyen sunucularda (ve tek iş varken) sırayla çalış
    if not claude or not cfg.get("ARKA_PLAN_ISLERI", True) or len(isler) == 1:
        for m, y in isler:
            kaydet(m, tek(m, y))
        return
    with ThreadPoolExecutor(max_workers=4) as havuz:
        gelecekler = {havuz.submit(tek, m, y): m for m, y in isler}
        for gelecek in as_completed(gelecekler):
            kaydet(gelecekler[gelecek], gelecek.result())


def puanlari_guncelle(depo: Depo, sehir_id: int) -> None:
    """Varsayılan ağırlıklarla puanları hesaplayıp kaydeder (sıralama ve 'en iyiler' için)."""
    mekanlar = depo.sehir_mekanlari(sehir_id)
    yorumlar = depo.sehir_yorumlari(sehir_id)
    puanlar = [m["google_puan"] for m in mekanlar if m.get("google_puan")]
    ort = statistics.mean(puanlar) if puanlar else 4.2
    for m in mekanlar:
        p = pusula_puani(m, yorumlar.get(m["id"], []), ort)
        depo.puan_kaydet(m["id"], p["puan"])


def claude_analizi_gerekli_mi(cfg, mekan: dict) -> bool:
    """Mekan sayfası açılınca Claude analizi yapılmalı mı? (Toplu analiz kapalıysa)"""
    return (not cfg.get("CLAUDE_TOPLU_ANALIZ", True) and bool(cfg.get("ANTHROPIC_API_KEY"))
            and mekan.get("kaynak") == "google"
            and (mekan.get("analiz") or {}).get("yontem") != "claude")


def mekan_yeniden_analiz(cfg, depo: Depo, ilerleme, mekan_id: int) -> str:
    ilerleme(20, "Yorumlar yeniden okunuyor")
    analizleri_yap(cfg, depo, [mekan_id], ilerleme, 20, 90)
    puanlari_guncelle(depo, depo.mekan(mekan_id)["sehir_id"])
    return f"/mekan/{mekan_id}"


# ---------------------------------------------------------------- menü
def menu_tara(cfg, depo: Depo, ilerleme, mekan_id: int) -> str:
    """Google'ın verdiği fotoğraflarda menü arar ve ürünleri okur (Claude görsel analizi)."""
    claude = _claude(cfg)
    if not claude:
        raise RuntimeError("Menü okumak için ANTHROPIC_API_KEY gerekli.")
    fotolar = [f for f in depo.fotolar(mekan_id) if f["kaynak"] == "google"][:10]
    if not fotolar:
        depo.menu_kaydet(mekan_id, {"durum": "yok", "kaynak": "google",
                                    "not": "Google bu mekan için fotoğraf vermedi.",
                                    "tarandi": simdi_iso()})
        return f"/mekan/{mekan_id}"
    gp = google_istemcisi(cfg, depo)
    ilerleme(20, "Fotoğraf adresleri alınıyor")
    urller = []
    for f in fotolar:
        uri = gp.foto_uri(f["ref"])
        depo.foto_uri_kaydet(f["id"], uri)
        urller.append(uri)
    ilerleme(50, "Claude fotoğraflarda menü arıyor")
    sonuc = menu_oku(claude, urller)
    menu_foto_idleri = []
    for sira, f in enumerate(fotolar, 1):
        menu_mu = sira in sonuc["menu_fotolari"]
        depo.foto_menu_isaretle(f["id"], menu_mu)
        if menu_mu:
            menu_foto_idleri.append(f["id"])
    if menu_foto_idleri:
        menu = {"durum": "bulundu", "kaynak": "google_gorsel", "urunler": sonuc["urunler"],
                "foto_idleri": menu_foto_idleri, "en_yeni_tarih": None,
                "not": sonuc.get("not") or "", "tarandi": simdi_iso(),
                "tarih_notu": "Google'ın resmi API'si fotoğrafların yüklenme tarihini vermiyor. "
                              "Tarih için derin analiz yapabilirsiniz."}
    else:
        menu = {"durum": "yok", "kaynak": "google_gorsel", "urunler": [], "tarandi": simdi_iso(),
                "not": f"Google'ın verdiği {len(fotolar)} fotoğrafın hiçbiri menü değil. "
                       "Derin analiz, Google Haritalar'daki menü kategorisine doğrudan bakar."}
    depo.menu_kaydet(mekan_id, menu)
    puanlari_guncelle(depo, depo.mekan(mekan_id)["sehir_id"])
    return f"/mekan/{mekan_id}"


# ---------------------------------------------------------------- derin analiz
def derin_analiz(cfg, depo: Depo, ilerleme, mekan_id: int) -> str:
    """SerpApi: 30 güncel yorum + tarihli menü fotoğrafları, sonra yeniden analiz."""
    from .kaynaklar.serpapi import SerpApi

    mekan = depo.mekan(mekan_id)
    if mekan["kaynak"] != "google":
        raise RuntimeError("Derin analiz sadece gerçek Google verisinde çalışır.")
    sa = SerpApi(cfg["SERPAPI_API_KEY"])
    ilerleme(10, "Mekan SerpApi'de bulunuyor")
    data_id = sa.data_id_bul(mekan["place_id"])
    ilerleme(25, "Güncel yorumlar çekiliyor")
    for y in sa.yorumlar(data_id, adet=int(cfg.get("DERIN_YORUM_ADEDI", 30))):
        depo.yorum_ekle(mekan_id, "serpapi", y)
    ilerleme(50, "Menü fotoğrafları ve tarihleri çekiliyor")
    menu_fotolari = sa.menu_fotolari(data_id, adet=4)
    for sira, f in enumerate(menu_fotolari):
        depo.foto_ekle(mekan_id, "serpapi", f, sira=20 + sira)
    if menu_fotolari:
        tarihler = sorted(f["yukleme_tarihi"] for f in menu_fotolari if f.get("yukleme_tarihi"))
        menu = {"durum": "bulundu", "kaynak": "serpapi", "urunler": [],
                "en_yeni_tarih": tarihler[-1] if tarihler else None, "tarandi": simdi_iso(),
                "not": ""}
        claude = _claude(cfg)
        if claude:
            ilerleme(65, "Claude menüdeki ürünleri okuyor")
            try:
                sonuc = menu_oku(claude, [f["ref"] for f in menu_fotolari], hepsi_menu=True)
                menu["urunler"] = sonuc["urunler"]
                menu["not"] = sonuc.get("not") or ""
            except YapayZekaHatasi as e:
                menu["not"] = f"Menü fotoğrafları bulundu ama okunamadı: {e}"
        depo.menu_kaydet(mekan_id, menu)
    ilerleme(80, "Tüm yorumlarla yeniden analiz ediliyor")
    analizleri_yap(cfg, depo, [mekan_id], lambda *_: None)
    depo.derin_analiz_isaretle(mekan_id)
    puanlari_guncelle(depo, mekan["sehir_id"])
    ilerleme(100, f"Derin analiz bitti ({sa.harcanan} SerpApi araması)")
    return f"/mekan/{mekan_id}"
