"""İnternete açık kullanım: şifreli giriş, PWA dosyaları, thread'siz (PythonAnywhere) mod."""
import pytest

from conftest import SahteOturum, veri
from pusula import create_app, tarama
from pusula.db import Depo, baglan
from pusula.iller import il_bul


@pytest.fixture
def sifreli(tmp_path):
    app = create_app({"VERITABANI": str(tmp_path / "s.sqlite3"), "DEMO": True, "ISLER_SENKRON": True,
                      "TESTING": True, "SECRET_KEY": "t", "APP_SIFRESI": "gizli-sifre",
                      "GOOGLE_PLACES_API_KEY": "", "ANTHROPIC_API_KEY": "", "SERPAPI_API_KEY": ""})
    return app.test_client()


def test_sifresiz_erisim_engellenir(sifreli):
    r = sifreli.get("/sehir/konya")
    assert r.status_code == 302 and "/giris" in r.headers["Location"]
    assert sifreli.post("/liste/1", headers={"X-Requested-With": "fetch"}).status_code == 401
    assert sifreli.get("/api/is/1").status_code == 401


def test_pwa_dosyalari_giris_olmadan_acik(sifreli):
    assert sifreli.get("/static/manifest.webmanifest").status_code == 200
    r = sifreli.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["Content-Type"]
    assert sifreli.get("/cevrimdisi").status_code == 200
    assert sifreli.get("/static/ikon/ikon-192.png").status_code == 200


def test_giris_ve_cikis(sifreli):
    r = sifreli.post("/giris?sonra=/listem", data={"sifre": "yanlis"})
    assert "Şifre yanlış" in r.get_data(as_text=True)
    r = sifreli.post("/giris?sonra=/listem", data={"sifre": "gizli-sifre"})
    assert r.status_code == 302 and r.headers["Location"] == "/listem"
    assert sifreli.get("/").status_code == 200
    sifreli.post("/cikis")
    assert sifreli.get("/").status_code == 302


def test_giris_dis_adrese_yonlendirmez(sifreli):
    r = sifreli.post("/giris?sonra=//kotu.site", data={"sifre": "gizli-sifre"})
    assert r.headers["Location"] == "/"


def test_kaba_kuvvet_sinirlanir(sifreli, monkeypatch):
    monkeypatch.setattr("pusula.web.time.sleep", lambda s: None)
    for _ in range(5):
        sifreli.post("/giris", data={"sifre": "x"})
    r = sifreli.post("/giris", data={"sifre": "gizli-sifre"})
    assert r.status_code == 429


def test_threadsiz_mod_claude_mekan_acilinca(tmp_path, monkeypatch):
    """PythonAnywhere modu: tarama kural analiziyle biter, Claude analizi mekan açılınca yapılır."""
    import pusula.kaynaklar.google_places as gp_mod
    monkeypatch.setattr(gp_mod.requests, "Session", lambda: SahteOturum([veri("places_yanit.json")]))
    claude_cagrilari = []

    def sahte_claude(claude, mekan, yorumlar):
        claude_cagrilari.append(mekan["ad"])
        return {"yontem": "claude", "ozet": "Claude özeti", "artilar": ["Lezzetli"], "eksiler": [],
                "kriterler": {"lezzet": 9}, "one_cikan_lezzetler": [], "uyarilar": [],
                "turist_tuzagi_riski": False, "kimlere_uygun": [], "kisi_basi_tahmin_tl": None,
                "yorum_adedi": len(yorumlar)}
    monkeypatch.setattr(tarama, "yorumlari_analiz_et", sahte_claude)

    app = create_app({"VERITABANI": str(tmp_path / "p.sqlite3"), "DEMO": False, "TESTING": True,
                      "SECRET_KEY": "t", "GOOGLE_PLACES_API_KEY": "K", "ANTHROPIC_API_KEY": "C",
                      "SERPAPI_API_KEY": "", "ARKA_PLAN_ISLERI": False, "ISLER_SENKRON": True,
                      "CLAUDE_TOPLU_ANALIZ": False, "MENU_TARAMA_LIMITI": 8, "APP_SIFRESI": ""})
    c = app.test_client()
    r = c.post("/tara", data={"sehir": "konya", "hedef": "20"})
    assert c.get(r.headers["Location"].replace("/is/", "/api/is/")).get_json()["durum"] == "bitti"
    assert claude_cagrilari == []  # tarama sırasında Claude çağrılmadı, menü taraması da yapılmadı
    conn = baglan(app.config["VERITABANI"])
    d = Depo(conn)
    kebap = next(m for m in d.sehir_mekanlari(d.sehir_slug("konya")["id"]) if m["kategori"] == "kebap")
    assert kebap["analiz"]["yontem"] == "kural"
    sayfa = c.get(f"/mekan/{kebap['id']}").get_data(as_text=True)
    assert "Claude özeti" in sayfa and claude_cagrilari == [kebap["ad"]]
    c.get(f"/mekan/{kebap['id']}")
    assert len(claude_cagrilari) == 1  # ikinci açılışta tekrar çağrılmaz
    conn.close()
