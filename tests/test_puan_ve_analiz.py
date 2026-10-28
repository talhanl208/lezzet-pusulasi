from datetime import date, timedelta

from pusula import analiz_kural
from pusula.puanlama import (agirliklari_duzelt, bayes_puani, fiyat_etiketi, kisi_basi_tl,
                             kriter_bileseni, pusula_puani, rozet_belirle, trend_hesapla)


def test_az_yorumlu_5_yildiz_cok_yorumlu_4_6yi_gecemez():
    ort = 4.3
    az = bayes_puani(5.0, 12, ort)
    cok = bayes_puani(4.6, 8000, ort)
    assert cok > az


def test_kriter_agirliklari_puani_degistirir():
    kriterler = {"lezzet": 9, "fiyat_performans": 3, "servis": 6, "temizlik": 6,
                 "ambiyans": 6, "hiz": 6}
    lezzetci, _ = agirliklari_duzelt({"lezzet": 100, "fiyat_performans": 0, "servis": 0,
                                      "temizlik": 0, "ambiyans": 0, "hiz": 0})
    hesapci, _ = agirliklari_duzelt({"lezzet": 0, "fiyat_performans": 100, "servis": 0,
                                     "temizlik": 0, "ambiyans": 0, "hiz": 0})
    assert kriter_bileseni(kriterler, lezzetci) == 9
    assert kriter_bileseni(kriterler, hesapci) == 3


def test_kanit_olmayan_kriter_hesaba_katilmaz():
    agirlik, _ = agirliklari_duzelt(None)
    assert kriter_bileseni({"lezzet": 8, "servis": None}, agirlik) == 8


def test_trend_son_6_ay_kotu():
    bugun = date.today()
    yorumlar = [{"puan": 2, "tarih": (bugun - timedelta(days=10 * i)).isoformat()} for i in range(1, 7)]
    t = trend_hesapla(yorumlar, 4.5)
    assert t["fark"] < -2 and t["etki"] < 0


def test_pusula_puani_ve_rozetler():
    mekan = {"google_puan": 4.8, "yorum_sayisi": 120, "fiyat_seviyesi": 1,
             "analiz": {"kriterler": {"lezzet": 9, "fiyat_performans": 9, "servis": 8,
                                      "temizlik": 9, "ambiyans": 7, "hiz": 8},
                        "turist_tuzagi_riski": False}}
    p = pusula_puani(mekan, [], 4.3)
    assert 7 <= p["puan"] <= 10
    rozetler = rozet_belirle(mekan, p)
    assert "gizli_hazine" in rozetler and "uygun_fiyat" in rozetler


def test_fiyat():
    assert kisi_basi_tl({"fiyat_min": 400, "fiyat_max": 600}) == 500
    assert fiyat_etiketi({"fiyat_min": 400, "fiyat_max": 600}) == "₺400–600"
    assert fiyat_etiketi({"fiyat_seviyesi": 3}) == "₺₺₺"


def _y(metin, puan):
    return {"metin": metin, "puan": puan, "tarih": date.today().isoformat()}


def test_kural_analizi_olumlu_ve_olumsuz_ayirir():
    iyi = analiz_kural.analiz_et({}, [
        _y("Adana kebap enfes, çok lezzetliydi. Garsonlar çok ilgili.", 5),
        _y("Yemekler harika, fiyatlar uygun ve porsiyonlar doyurucu.", 5),
        _y("Lezzet olarak şehrin en iyisi, mekan tertemiz.", 5),
    ])
    kotu = analiz_kural.analiz_et({}, [
        _y("Yemekler lezzetsiz ve soğuk geldi. Garson kaba.", 1),
        _y("Masalar kirliydi, tuvalet pis. Bir daha gelmem.", 1),
        _y("Çok pahalı, porsiyonlar az geldi.", 2),
    ])
    assert iyi["kriterler"]["lezzet"] > kotu["kriterler"]["lezzet"]
    assert iyi["kriterler"]["servis"] > kotu["kriterler"]["servis"]
    assert "Adana kebap" in iyi["one_cikan_lezzetler"]
    assert iyi["artilar"] and kotu["eksiler"]
    assert any("Temizlik" in e for e in kotu["eksiler"])


def test_olumsuzlama_degil():
    a = analiz_kural.analiz_et({}, [_y("Mekan hiç temiz değil.", 3), _y("Tuvalet temiz değildi.", 3)])
    assert a["kriterler"]["temizlik"] <= 5


def test_turist_tuzagi_ve_uyarilar():
    a = analiz_kural.analiz_et({}, [
        _y("Menüde fiyat yazmıyor, hesap gelince şok olduk, tam kazık.", 1),
        _y("Fahiş fiyat. Kart geçmiyor, sadece nakit.", 1),
    ])
    assert a["turist_tuzagi_riski"] is True
    assert any("nakit" in u for u in a["uyarilar"])


def test_kisi_basi_fiyat_yorumdan():
    a = analiz_kural.analiz_et({}, [_y("Kişi başı 450 TL ödedik, değdi.", 5),
                                    _y("Kişi başı 550 TL civarı.", 4)])
    assert a["kisi_basi_tahmin_tl"] == 500
