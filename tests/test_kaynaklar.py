"""Dış servis istemcileri: gerçek ağ yerine sahte yanıtlarla test edilir."""
import pytest

from conftest import SahteOturum, SahteYanit, veri
from pusula.kaynaklar.google_places import ALAN_MASKESI, GooglePlaces, GooglePlacesHatasi, donustur
from pusula.kaynaklar.serpapi import SerpApi, yorum_donustur
from pusula.yapay_zeka import Claude, analizi_temizle, menu_oku, yorumlari_analiz_et


def test_places_metin_arama_istegi():
    oturum = SahteOturum([veri("places_yanit.json")])
    gp = GooglePlaces("ANAHTAR", oturum=oturum)
    yerler, token = gp.metin_ara("Konya restoran", 37.87, 32.49, 12000)
    istek = oturum.istekler[0]
    assert istek["url"].endswith("/places:searchText")
    assert istek["headers"]["X-Goog-Api-Key"] == "ANAHTAR"
    assert "places.reviews" in istek["headers"]["X-Goog-FieldMask"]
    assert istek["json"]["languageCode"] == "tr" and istek["json"]["regionCode"] == "TR"
    assert len(yerler) == 5 and token == "SAYFA2"


def test_places_hata_mesaji():
    oturum = SahteOturum([SahteYanit({"error": {"message": "API key not valid"}}, durum=400)])
    with pytest.raises(GooglePlacesHatasi, match="API key not valid"):
        GooglePlaces("x", oturum=oturum).metin_ara("a", 0, 0, 1000)


def test_places_donustur():
    k = donustur(veri("places_yanit.json")["places"][0])
    assert k["place_id"] == "ChIJ_ornek_kebap"
    assert k["ad"] == "Örnek Usta Kebap Salonu"
    assert k["ilce"] == "Karatay"
    assert k["kategori"] == "kebap"
    assert (k["fiyat_seviyesi"], k["fiyat_min"], k["fiyat_max"]) == (2, 400, 600)
    assert k["google_ozet"].startswith("Ziyaretçiler")
    assert k["ozellikler"]["paket"] is True and k["ozellikler"]["otopark"] is True
    assert len(k["yorumlar"]) == 2 and k["yorumlar"][0]["yazar"] == "Ayşe K."
    assert k["fotolar"][0]["ref"] == "places/ChIJ_ornek_kebap/photos/p1"
    assert "places.photos" in ALAN_MASKESI


def test_places_foto_uri():
    oturum = SahteOturum([{"name": "x", "photoUri": "https://lh3.googleusercontent.com/abc"}])
    uri = GooglePlaces("K", oturum=oturum).foto_uri("places/a/photos/b")
    assert uri.startswith("https://lh3")
    assert oturum.istekler[0]["params"]["skipHttpRedirect"] == "true"


def test_serpapi_yorum_ve_menu_fotolari():
    oturum = SahteOturum([
        {"categories": [{"title": "Tümü", "id": "1"}, {"title": "Menü", "id": "CgIgAQ"}], "photos": []},
        {"photos": [{"image": "https://lh5.googleusercontent.com/m1",
                     "photo_meta_serpapi_link": "https://serpapi.com/search.json?engine=google_maps_photo_meta&data_id=x"}]},
        {"date": "29-8-2025"},
    ])
    sa = SerpApi("K", oturum=oturum)
    fotolar = sa.menu_fotolari("0x1:0x2", adet=2)
    assert fotolar == [{"kaynak": "serpapi", "ref": "https://lh5.googleusercontent.com/m1",
                        "kategori": "menu", "menu_mu": 1, "yukleme_tarihi": "2025-08-29"}]
    assert oturum.istekler[1]["params"]["category_id"] == "CgIgAQ"
    y = yorum_donustur({"user": {"name": "Can"}, "rating": 4.0, "date": "3 ay önce",
                        "iso_date": "2026-07-01T00:00:00Z", "snippet": "Güzel"})
    assert y["puan"] == 4 and y["tarih"].startswith("2026-07-01")


def _claude_yaniti(arac, girdi):
    return {"content": [{"type": "tool_use", "id": "t1", "name": arac, "input": girdi}]}


def test_claude_analiz_istegi_ve_temizleme():
    oturum = SahteOturum([_claude_yaniti("analiz_kaydet", {
        "ozet": "Kebapları övülüyor.", "artilar": ["Lezzetli"], "eksiler": [],
        "kriterler": {"lezzet": 12, "fiyat_performans": "7", "servis": None, "temizlik": 8,
                      "ambiyans": 6, "hiz": 0},
        "one_cikan_lezzetler": ["Adana kebap"], "uyarilar": [], "turist_tuzagi_riski": False,
        "kimlere_uygun": [], "kisi_basi_tahmin_tl": "450"})])
    c = Claude("K", "claude-haiku-5-5", oturum=oturum)
    a = yorumlari_analiz_et(c, {"ad": "X", "google_puan": 4.5, "yorum_sayisi": 10},
                            [{"puan": 5, "metin": "Harika", "tarih": "2026-08-01"}])
    govde = oturum.istekler[0]["json"]
    assert govde["tool_choice"] == {"type": "tool", "name": "analiz_kaydet"}
    assert govde["model"] == "claude-haiku-5-5"
    assert oturum.istekler[0]["headers"]["anthropic-version"]
    assert a["kriterler"]["lezzet"] == 10 and a["kriterler"]["fiyat_performans"] == 7
    assert a["kriterler"]["servis"] is None and a["kriterler"]["hiz"] == 1
    assert a["kisi_basi_tahmin_tl"] == 450 and a["yontem"] == "claude"


def test_claude_menu_okuma():
    oturum = SahteOturum([_claude_yaniti("menu_kaydet", {
        "menu_fotolari": [2, 9], "urunler": [{"ad": "Adana", "fiyat": 520, "kategori": "kebap"},
                                             {"ad": "", "fiyat": 1, "kategori": "x"}],
        "para_birimi": "TRY", "not": ""})])
    sonuc = menu_oku(Claude("K", "m", oturum=oturum), ["https://a/1", "https://a/2"])
    assert sonuc["menu_fotolari"] == [2]  # 9 numaralı fotoğraf yok, elenir
    assert sonuc["urunler"] == [{"ad": "Adana", "fiyat": 520.0, "kategori": "kebap"}]
    icerik = oturum.istekler[0]["json"]["messages"][0]["content"]
    assert icerik[1] == {"type": "image", "source": {"type": "url", "url": "https://a/1"}}


def test_analizi_temizle_bos_girdi():
    a = analizi_temizle({}, 0)
    assert a["artilar"] == [] and all(v is None for v in a["kriterler"].values())


def test_gunluk_sinir_istek_gondermez(tmp_path):
    from pusula.db import Depo, baglan, sema_kur
    from pusula.kaynaklar.google_places import GunlukSinirHatasi
    conn = baglan(str(tmp_path / "s.sqlite3"))
    sema_kur(conn)
    depo = Depo(conn)
    oturum = SahteOturum([veri("places_yanit.json")])
    gp = GooglePlaces("K", oturum=oturum, sinir=lambda tur: depo.sayac_artir(f"google_{tur}", 2))
    gp.metin_ara("a", 0, 0, 1000)
    gp.metin_ara("b", 0, 0, 1000)
    with pytest.raises(GunlukSinirHatasi):
        gp.metin_ara("c", 0, 0, 1000)
    assert len(oturum.istekler) == 2  # üçüncü istek Google'a hiç gitmedi
    assert depo.bugunku_kullanim() == {"google_arama": 2}
    conn.close()
