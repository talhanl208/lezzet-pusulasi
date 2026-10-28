from datetime import date, datetime

from pusula.iller import ILLER, il_bul
from pusula.kategori import kategori_belirle, yemek_mekani_mi
from pusula.konum import TURKIYE, acik_mi, mesafe_km
from pusula.metin import bulunma, goreli_tarihten, kac_zaman_once, katla, slugla, tarih_coz
from pusula.yemekler import yemekleri_bul


def test_81_il_var_ve_plaka_benzersiz():
    assert len(ILLER) == 81
    assert len({il["plaka"] for il in ILLER}) == 81
    assert len({il["slug"] for il in ILLER}) == 81


def test_il_bul_farkli_yazimlar():
    assert il_bul("34")["ad"] == "İstanbul"
    assert il_bul("İSTANBUL")["plaka"] == 34
    assert il_bul("istanbul")["plaka"] == 34
    assert il_bul("Şanlıurfa")["plaka"] == 63
    assert il_bul("urfa")["plaka"] == 63
    assert il_bul("adapazarı")["plaka"] == 54
    assert il_bul("yok böyle şehir") is None


def test_turkce_metin():
    assert katla("İSKENDER Köfte") == "iskender kofte"
    assert katla("IĞDIR") == "igdir"
    assert slugla("Kahramanmaraş") == "kahramanmaras"
    assert bulunma("Konya") == "Konya'da"
    assert bulunma("İzmir") == "İzmir'de"
    assert bulunma("Muş") == "Muş'ta"


def test_goreli_tarih_ve_kac_zaman_once():
    bugun = date(2026, 10, 28)
    assert goreli_tarihten("3 ay önce", bugun) == date(2026, 7, 30)
    assert goreli_tarihten("bir yıl önce", bugun) == date(2025, 10, 28)
    assert goreli_tarihten("2 weeks ago", bugun) == date(2026, 10, 14)
    assert tarih_coz("29-8-2022") == date(2022, 8, 29)
    assert tarih_coz("2026-08-20T10:00:00Z") == date(2026, 8, 20)
    assert kac_zaman_once("2026-06-28", bugun) == "4 ay önce"
    assert kac_zaman_once("2025-02-28", bugun) == "1 yıl 8 ay önce"


def test_kategori():
    assert kategori_belirle("Hacı Usta Ocakbaşı", ["restaurant"]) == "kebap"
    assert kategori_belirle("Merkez Baklavacısı", ["bakery"]) == "tatli"
    assert kategori_belirle("Kumkapı Balıkçısı", ["restaurant"]) == "balik"
    assert kategori_belirle("Çıtır Burger", ["restaurant"]) == "fastfood"
    assert kategori_belirle("Lezzet Durağı", ["restaurant"], "pizza_restaurant") == "pizza"
    assert kategori_belirle("Sakura", ["japanese_restaurant"], "japanese_restaurant") == "dunya"
    assert kategori_belirle("Zeytin Ağacı", ["restaurant"], "restaurant", 4) == "fine"
    assert kategori_belirle("Zeytin Ağacı", ["restaurant"]) == "restoran"
    assert yemek_mekani_mi(["cafe", "food"])
    assert not yemek_mekani_mi(["lodging", "point_of_interest"])


def test_yemek_sozlugu_kelime_sinirlari():
    assert yemekleri_bul("Romantik bir akşamdı") == []
    assert yemekleri_bul("Tuvalet kötü durumdaydı") == []
    assert yemekleri_bul("Mantı harikaydı") == ["Mantı"]
    assert yemekleri_bul("İnegöl köftesi efsane") == ["İnegöl köfte"]


def test_mesafe():
    # Konya merkez → Kayseri merkez ~ 240 km kuş uçuşu
    km = mesafe_km(37.8746, 32.4932, 38.7312, 35.4787)
    assert 230 < km < 280


def test_acik_mi():
    # Pazartesi 11:00-23:00 (Google: gün 1)
    p = [{"open": {"day": 1, "hour": 11, "minute": 0}, "close": {"day": 1, "hour": 23, "minute": 0}}]
    assert acik_mi(p, datetime(2026, 10, 26, 12, 0, tzinfo=TURKIYE)) is True   # Pazartesi
    assert acik_mi(p, datetime(2026, 10, 26, 23, 30, tzinfo=TURKIYE)) is False
    assert acik_mi(p, datetime(2026, 10, 27, 12, 0, tzinfo=TURKIYE)) is False  # Salı
    # Gece yarısını geçen: Cumartesi 18:00 → Pazar 02:00
    gece = [{"open": {"day": 6, "hour": 18, "minute": 0}, "close": {"day": 0, "hour": 2, "minute": 0}}]
    assert acik_mi(gece, datetime(2026, 11, 1, 1, 0, tzinfo=TURKIYE)) is True   # Pazar 01:00
    assert acik_mi(gece, datetime(2026, 11, 1, 3, 0, tzinfo=TURKIYE)) is False
    # 7/24 açık
    assert acik_mi([{"open": {"day": 0, "hour": 0, "minute": 0}}]) is True
    assert acik_mi([]) is None
