"""Uçtan uca: demo modunda tarama + sayfalar, gerçek modda sahte Google ile tarama."""
from conftest import SahteOturum, veri
from pusula import tarama
from pusula.db import Depo, baglan
from pusula.iller import il_bul


def _tara(istemci, sehir="konya"):
    r = istemci.post("/tara", data={"sehir": sehir, "hedef": "50"})
    assert r.status_code == 302 and "/is/" in r.headers["Location"]
    durum = istemci.get(r.headers["Location"].replace("/is/", "/api/is/")).get_json()
    assert durum["durum"] == "bitti", durum
    return durum


def test_demo_tarama_ve_sayfalar(istemci):
    _tara(istemci)
    for url in ["/", "/sehir/konya", "/sehir/konya?kat=kebap&sirala=fiyat_artan",
                "/sehir/konya?q=etli+ekmek", "/sehir/konya?acik=1&fiyat=1",
                "/sehir/konya?ref=nokta&lat=37.87&lng=32.49&sirala=mesafe&max_km=2",
                "/mekan/1", "/mekan/2?sans=1", "/karsilastir?m=1&m=2", "/listem", "/foto/1",
                "/sehir/konya/liste.csv"]:
        r = istemci.get(url)
        assert r.status_code == 200, url
    assert istemci.get("/sehir/konya/rastgele").status_code == 302
    assert istemci.get("/yok").status_code == 404


def test_sirala_ve_filtre(istemci):
    _tara(istemci)
    sayfa = istemci.get("/sehir/konya?kat=tatli").get_data(as_text=True)
    assert "Tatlı &amp; pastane" in sayfa
    assert "Kebap Salonu" not in sayfa


def test_gezi_listesi_ve_agirliklar(istemci):
    _tara(istemci)
    r = istemci.post("/liste/3", headers={"X-Requested-With": "fetch"})
    assert r.get_json() == {"ekli": True, "adet": 1}
    assert istemci.post("/liste/3", headers={"X-Requested-With": "fetch"}).get_json()["ekli"] is False
    r = istemci.post("/ayarlar/puan", data={"lezzet": "100", "servis": "0", "fiyat_performans": "0",
                                             "temizlik": "0", "ambiyans": "0", "hiz": "0",
                                             "google": "0", "geri": "//kotu.site"})
    assert r.headers["Location"] == "/"  # dış adrese yönlendirme yok
    with istemci.session_transaction() as s:
        assert s["agirlik"]["lezzet"] == 100 and s["agirlik"]["google"] == 0


def test_yaricapa_ve_ture_gore_eleme(uygulama, monkeypatch):
    """Gerçek mod: otel, kapanmış ve çok uzak mekanlar listeye girmez."""
    sahte = SahteOturum([veri("places_yanit.json")])
    import pusula.kaynaklar.google_places as gp_mod
    monkeypatch.setattr(gp_mod.requests, "Session", lambda: sahte)
    cfg = dict(uygulama.config, DEMO=False, GOOGLE_PLACES_API_KEY="K", MENU_TARAMA_LIMITI=0)
    conn = baglan(cfg["VERITABANI"])
    depo = Depo(conn)
    tarama.sehir_tara(cfg, depo, lambda *_: None, il_bul("konya"), hedef=20)
    sehir = depo.sehir_slug("konya")
    adlar = sorted(m["ad"] for m in depo.sehir_mekanlari(sehir["id"]))
    assert adlar == ["Merkez Baklavacısı", "Örnek Usta Kebap Salonu"]
    kebap = next(m for m in depo.sehir_mekanlari(sehir["id"]) if m["kategori"] == "kebap")
    assert kebap["analiz"]["yontem"] == "kural"
    assert len(depo.yorumlar(kebap["id"])) == 2
    assert kebap["pusula_puani"] is not None
    conn.close()


def test_sinir_dolunca_eldekilerle_devam(uygulama, monkeypatch):
    sahte = SahteOturum([veri("places_yanit.json")])
    import pusula.kaynaklar.google_places as gp_mod
    monkeypatch.setattr(gp_mod.requests, "Session", lambda: sahte)
    cfg = dict(uygulama.config, DEMO=False, GOOGLE_PLACES_API_KEY="K", MENU_TARAMA_LIMITI=0,
               GUNLUK_ARAMA_LIMITI=1)
    conn = baglan(cfg["VERITABANI"])
    depo = Depo(conn)
    mesajlar = []
    tarama.sehir_tara(cfg, depo, lambda y, m: mesajlar.append(m), il_bul("konya"), hedef=50)
    assert len(sahte.istekler) == 1
    assert any("sınırı doldu" in m for m in mesajlar)
    assert len(depo.sehir_mekanlari(depo.sehir_slug("konya")["id"])) == 2
    conn.close()
