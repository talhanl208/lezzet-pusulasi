"""Sayfalar ve uç noktalar."""
from __future__ import annotations

import csv
import hmac
import io
import json
import random
import time
from datetime import datetime, timedelta, timezone

from urllib.parse import urlencode

from flask import (Blueprint, Response, abort, current_app, flash, jsonify, redirect,
                   render_template, request, send_from_directory, session, url_for)

from werkzeug.datastructures import MultiDict

from . import depo, isler, tarama
from .gorsel import demo_svg, yer_tutucu_svg
from .iller import ILLER, il_bul
from .kategori import KATEGORILER, kategori_adi, kategori_emoji
from .konum import mesafe_km, mesafe_yazi
from .liste import (OZELLIKLER, SIRALAMALAR, filtre_oku, rota_sirala, rota_uzunlugu, uygula,
                    zenginlestir)
from .metin import bin_ayrac, bulunma, kac_zaman_once, tarih_coz
from .puanlama import KRITERLER, ROZETLER, VARSAYILAN_AGIRLIK, agirliklari_duzelt, puan_rengi

bp = Blueprint("pusula", __name__)
MAKS_LISTE = 30


def sablon_ayarlari(app):
    app.jinja_env.filters.update(
        bin=bin_ayrac, bulunma=bulunma, once=kac_zaman_once, mesafe=mesafe_yazi, kat_adi=kategori_adi,
        kat_emoji=kategori_emoji, renk=puan_rengi,
        virgul=lambda x, n=1: "" if x is None else f"{x:.{n}f}".replace(".", ","))

    @app.template_global()
    def sorgu_ile(**degisen):
        """Mevcut sorgu parametrelerini koruyarak bazılarını değiştirir."""
        args = request.args.copy()
        for k, v in degisen.items():
            args.pop(k, None)
            if v is not None:
                args[k] = v
        return urlencode(list(args.items(multi=True)))

    @app.context_processor
    def ortak():
        return {
            "demo": current_app.config["DEMO"],
            "ROZETLER": ROZETLER, "KRITERLER": KRITERLER, "KATEGORILER": KATEGORILER,
            "gezi_listesi": session.get("liste", []),
            "claude_var": bool(current_app.config["ANTHROPIC_API_KEY"]),
            "serp_var": bool(current_app.config["SERPAPI_API_KEY"]),
            "sifre_var": bool(current_app.config["APP_SIFRESI"]),
        }


# ------------------------------------------------------------------ giriş
_ACIK_UCLAR = {"static", "pusula.giris", "pusula.servis_calisani", "pusula.cevrimdisi"}
_HATALI_DENEMELER: dict[str, list[float]] = {}


@bp.before_app_request
def giris_kontrol():
    if not current_app.config.get("APP_SIFRESI") or request.endpoint in _ACIK_UCLAR:
        return None
    if session.get("giris"):
        return None
    if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"hata": "Giriş gerekli"}), 401
    return redirect(url_for("pusula.giris", sonra=request.full_path))


@bp.route("/giris", methods=["GET", "POST"])
def giris():
    sonra = request.args.get("sonra") or "/"
    if not sonra.startswith("/") or sonra.startswith(("//", "/\\")):
        sonra = "/"
    hata = None
    if request.method == "POST":
        ip = request.headers.get("X-Real-IP") or request.remote_addr or "?"
        simdi = time.time()
        denemeler = [t for t in _HATALI_DENEMELER.get(ip, []) if simdi - t < 600]
        if len(denemeler) >= 5:
            hata = "Çok fazla hatalı deneme. 10 dakika sonra tekrar deneyin."
        elif hmac.compare_digest(request.form.get("sifre", "").encode(),
                                 current_app.config["APP_SIFRESI"].encode()):
            _HATALI_DENEMELER.pop(ip, None)
            session.clear()
            session.permanent = True
            session["giris"] = True
            return redirect(sonra)
        else:
            denemeler.append(simdi)
            _HATALI_DENEMELER[ip] = denemeler
            time.sleep(1)
            hata = "Şifre yanlış."
    return render_template("giris.html", hata=hata, sonra=sonra), (429 if hata and "fazla" in hata else 200)


@bp.post("/cikis")
def cikis():
    session.clear()
    return redirect(url_for("pusula.giris"))


@bp.route("/sw.js")
def servis_calisani():
    yanit = send_from_directory(current_app.static_folder, "sw.js", mimetype="text/javascript")
    yanit.headers["Cache-Control"] = "no-cache"
    return yanit


@bp.route("/cevrimdisi")
def cevrimdisi():
    return render_template("cevrimdisi.html")


def _agirlik():
    return agirliklari_duzelt(session.get("agirlik"))


def _sehir_veya_404(slug):
    sehir = depo().sehir_slug(slug)
    if not sehir:
        il = il_bul(slug)
        if il:
            return redirect(url_for(".index", sehir=il["ad"]))
        abort(404)
    return sehir


def _sehir_mekanlari(sehir, ref=None):
    d = depo()
    agirlik, google_payi = _agirlik()
    return zenginlestir(d.sehir_mekanlari(sehir["id"]), d.sehir_yorumlari(sehir["id"]),
                        d.kapak_fotolari(sehir["id"]), sehir, agirlik, google_payi, ref)


def _harita_modu():
    if current_app.config["DEMO"]:
        return "leaflet"
    # Google Places verisi Google dışı haritada gösterilemez (kullanım şartları).
    return "google" if current_app.config["GOOGLE_MAPS_JS_KEY"] else "yok"


def _json(veri) -> str:
    """<script> içine gömülecek JSON; '</' dizisi etiketi kapatmasın."""
    return json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")


def _harita_noktalari(mekanlar):
    return [{"id": m["id"], "ad": m["ad"], "lat": m["lat"], "lng": m["lng"],
             "puan": m["puan"].get("puan"), "renk": puan_rengi(m["puan"].get("puan")),
             "google": m.get("google_puan"), "kat": kategori_emoji(m.get("kategori")),
             "fiyat": m.get("fiyat_etiketi"), "url": url_for(".mekan", mekan_id=m["id"])}
            for m in mekanlar if m.get("lat") is not None]


# ------------------------------------------------------------------ ana sayfa
@bp.route("/")
def index():
    return render_template("index.html", iller=ILLER, taranmis=depo().taranmis_sehirler(),
                           secili=request.args.get("sehir", ""),
                           hedef=current_app.config["VARSAYILAN_HEDEF"])


@bp.post("/tara")
def tara():
    il = il_bul(request.form.get("sehir"))
    if not il:
        flash("Şehri bulamadık. Listeden bir il seçin ya da plaka kodunu yazın (ör. 42).")
        return redirect(url_for(".index"))
    bolge = (request.form.get("bolge") or "").strip()[:40]
    try:
        hedef = max(20, min(120, int(request.form.get("hedef") or 50)))
    except ValueError:
        hedef = 50
    sehir = depo().sehir_slug(il["slug"])
    zorla = request.form.get("zorla") == "1"
    if sehir and sehir.get("son_tarama") and not zorla and not bolge:
        son = datetime.fromisoformat(sehir["son_tarama"])
        if datetime.now(timezone.utc) - son < timedelta(days=current_app.config["YENILEME_GUN"]):
            return redirect(url_for(".sehir", slug=il["slug"]))
    is_id = isler.baslat(current_app._get_current_object(), "tarama",
                         f"tara:{il['slug']}:{bolge}", tarama.sehir_tara, il, hedef, bolge)
    return redirect(url_for(".is_sayfasi", is_id=is_id))


@bp.route("/is/<int:is_id>")
def is_sayfasi(is_id):
    kayit = depo().is_kaydi(is_id) or abort(404)
    return render_template("is.html", kayit=kayit)


@bp.route("/api/is/<int:is_id>")
def is_durumu(is_id):
    kayit = depo().is_kaydi(is_id) or abort(404)
    return jsonify({k: kayit[k] for k in ("durum", "ilerleme", "mesaj", "sonuc_url", "log")})


# ------------------------------------------------------------------ şehir listesi
@bp.route("/sehir/<slug>")
def sehir(slug):
    sehir = _sehir_veya_404(slug)
    if not isinstance(sehir, dict):
        return sehir
    f = filtre_oku(request.args, current_app.config["VARSAYILAN_HEDEF"])
    ref = (f.lat, f.lng) if f.ref != "merkez" else None
    tum = _sehir_mekanlari(sehir, ref)
    filtreli = uygula(tum, f)
    gosterilen = filtreli[:f.n]
    il = il_bul(sehir["plaka"])
    kat_sayilari = {}
    for m in tum:
        kat_sayilari[m["kategori"]] = kat_sayilari.get(m["kategori"], 0) + 1
    ilceler = sorted({m["ilce"] for m in tum if m.get("ilce")})
    agirlik, google_payi = _agirlik()
    return render_template(
        "sehir.html", sehir=sehir, il=il, f=f, mekanlar=gosterilen, toplam=len(tum),
        eslesen=len(filtreli), kat_sayilari=kat_sayilari, ilceler=ilceler,
        OZELLIKLER=OZELLIKLER, SIRALAMALAR=SIRALAMALAR, agirlik=agirlik, google_payi=google_payi,
        harita_modu=_harita_modu(),
        harita=_json({"merkez": [sehir["lat"], sehir["lng"]], "ref": [f.lat, f.lng] if ref else None,
                      "noktalar": _harita_noktalari(gosterilen)}),
        sorgu=request.query_string.decode())


@bp.route("/sehir/<slug>/rastgele")
def rastgele(slug):
    sehir = _sehir_veya_404(slug)
    if not isinstance(sehir, dict):
        return sehir
    f = filtre_oku(request.args)
    adaylar = uygula(_sehir_mekanlari(sehir), f)[:12]
    if not adaylar:
        flash("Bu filtrelerle seçilecek mekan kalmadı. Birkaç filtreyi kaldırıp tekrar deneyin.")
        return redirect(url_for(".sehir", slug=slug, **request.args))
    agirliklar = [max(0.5, (m["puan"].get("puan") or 5)) ** 2 for m in adaylar]
    secilen = random.choices(adaylar, weights=agirliklar, k=1)[0]
    return redirect(url_for(".mekan", mekan_id=secilen["id"], sans=1))


@bp.route("/sehir/<slug>/liste.csv")
def csv_indir(slug):
    sehir = _sehir_veya_404(slug)
    if not isinstance(sehir, dict):
        return sehir
    f = filtre_oku(request.args)
    tampon = io.StringIO()
    yazici = csv.writer(tampon, delimiter=";")
    yazici.writerow(["Sıra", "Mekan", "Kategori", "İlçe", "Pusula Puanı", "Google puanı",
                     "Yorum sayısı", "Fiyat", "Artılar", "Eksiler", "Adres", "Google Haritalar"])
    for i, m in enumerate(uygula(_sehir_mekanlari(sehir), f)[:f.n], 1):
        a = m.get("analiz") or {}
        yazici.writerow([i, m["ad"], kategori_adi(m["kategori"]), m.get("ilce") or "",
                         m["puan"].get("puan"), m.get("google_puan"), m.get("yorum_sayisi"),
                         m.get("fiyat_etiketi"), " | ".join(a.get("artilar") or []),
                         " | ".join(a.get("eksiler") or []), m.get("adres") or "",
                         m.get("maps_url") or ""])
    return Response("﻿" + tampon.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={slug}-restoranlar.csv"})


# ------------------------------------------------------------------ mekan detayı
@bp.route("/mekan/<int:mekan_id>")
def mekan(mekan_id):
    d = depo()
    ham = d.mekan(mekan_id) or abort(404)
    if tarama.claude_analizi_gerekli_mi(current_app.config, ham):
        # Toplu analiz kapalıysa (ör. PythonAnywhere) Claude analizi mekan ilk açıldığında yapılır
        try:
            tarama.analizleri_yap(current_app.config, d, [mekan_id], lambda *_: None)
            tarama.puanlari_guncelle(d, ham["sehir_id"])
        except Exception as e:  # analiz olmasa da sayfa açılsın
            current_app.logger.warning("Claude analizi yapılamadı: %s", e)
    sehir = d.sehir_id(ham["sehir_id"])
    tum = _sehir_mekanlari(sehir)
    sirali = uygula(tum, filtre_oku(MultiDict()))
    m = next(x for x in tum if x["id"] == mekan_id)
    sira = next((i for i, x in enumerate(sirali, 1) if x["id"] == mekan_id), None)
    benzerler = sorted(
        (x for x in tum if x["kategori"] == m["kategori"] and x["id"] != mekan_id),
        key=lambda x: mesafe_km(m["lat"], m["lng"], x["lat"], x["lng"]) or 0)[:4]
    for b in benzerler:
        b["uzaklik"] = mesafe_km(m["lat"], m["lng"], b["lat"], b["lng"])
    fotolar = d.fotolar(mekan_id)
    yorumlar = d.yorumlar(mekan_id)
    return render_template(
        "mekan.html", m=m, sehir=sehir, sira=sira, toplam=len(tum), benzerler=benzerler,
        fotolar=[f for f in fotolar if not f.get("menu_mu")],
        menu_fotolari=sorted([f for f in fotolar if f.get("menu_mu")],
                             key=lambda f: f.get("yukleme_tarihi") or "", reverse=True),
        yorumlar=yorumlar, sans=request.args.get("sans") == "1",
        agirlik=_agirlik()[0], harita_modu=_harita_modu(),
        harita=_json({"merkez": [m["lat"], m["lng"]], "ref": None, "yakin": True,
                      "noktalar": _harita_noktalari([m] + benzerler)}),
        tarih_coz=tarih_coz)


def _mekan_isi(mekan_id, tur, fonksiyon, kosul, mesaj):
    m = depo().mekan(mekan_id) or abort(404)
    if not kosul(m):
        flash(mesaj)
        return redirect(url_for(".mekan", mekan_id=mekan_id))
    is_id = isler.baslat(current_app._get_current_object(), tur, f"{tur}:{mekan_id}",
                         fonksiyon, mekan_id)
    return redirect(url_for(".is_sayfasi", is_id=is_id))


@bp.post("/mekan/<int:mekan_id>/menu")
def menu_tara(mekan_id):
    cfg = current_app.config
    return _mekan_isi(mekan_id, "menu", tarama.menu_tara,
                      lambda m: m["kaynak"] == "google" and cfg["ANTHROPIC_API_KEY"],
                      "Menü okuma için gerçek Google verisi ve ANTHROPIC_API_KEY gerekli.")


@bp.post("/mekan/<int:mekan_id>/derin")
def derin_analiz(mekan_id):
    cfg = current_app.config
    return _mekan_isi(mekan_id, "derin", tarama.derin_analiz,
                      lambda m: m["kaynak"] == "google" and cfg["SERPAPI_API_KEY"],
                      "Derin analiz için gerçek Google verisi ve SERPAPI_API_KEY gerekli.")


@bp.post("/mekan/<int:mekan_id>/analiz")
def yeniden_analiz(mekan_id):
    return _mekan_isi(mekan_id, "analiz", tarama.mekan_yeniden_analiz, lambda m: True, "")


# ------------------------------------------------------------------ fotoğraflar
@bp.route("/foto/<int:foto_id>")
def foto(foto_id):
    d = depo()
    f = d.foto(foto_id)
    if not f:
        return Response(yer_tutucu_svg(), mimetype="image/svg+xml")
    if f["kaynak"] == "demo":
        svg = demo_svg(f, d.mekan(f["mekan_id"]))
        return Response(svg, mimetype="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})
    if f["kaynak"] == "serpapi":
        return redirect(f["ref"])
    if f.get("uri_onbellek") and f.get("uri_tarih"):
        yas = datetime.now(timezone.utc) - datetime.fromisoformat(f["uri_tarih"])
        if yas < timedelta(hours=current_app.config["FOTO_URI_SAAT"]):
            return redirect(f["uri_onbellek"])
    if current_app.config["DEMO"] or not current_app.config["GOOGLE_PLACES_API_KEY"]:
        return Response(yer_tutucu_svg(), mimetype="image/svg+xml")
    from .kaynaklar.google_places import GooglePlacesHatasi
    try:
        uri = tarama.google_istemcisi(current_app.config, d).foto_uri(f["ref"])
    except (GooglePlacesHatasi, OSError):
        return Response(yer_tutucu_svg(), mimetype="image/svg+xml")
    d.foto_uri_kaydet(foto_id, uri)
    return redirect(uri)


# ------------------------------------------------------------------ karşılaştırma
@bp.route("/karsilastir")
def karsilastir():
    idler = [int(i) for i in request.args.getlist("m") if i.isdigit()][:3]
    d = depo()
    secilenler = d.mekanlar(idler)
    if len(secilenler) < 2:
        flash("Karşılaştırmak için listeden en az iki mekan seçin.")
        return redirect(request.referrer or url_for(".index"))
    sehirler = {m["sehir_id"] for m in secilenler}
    zengin = []
    for sehir_id in sehirler:
        sehir = d.sehir_id(sehir_id)
        zengin += [m for m in _sehir_mekanlari(sehir) if m["id"] in idler]
    zengin.sort(key=lambda m: idler.index(m["id"]))
    en_iyi = max(zengin, key=lambda m: m["puan"].get("puan") or 0)["id"]
    return render_template("karsilastir.html", mekanlar=zengin, en_iyi=en_iyi)


# ------------------------------------------------------------------ gezi listesi
@bp.post("/liste/<int:mekan_id>")
def liste_degistir(mekan_id):
    liste = list(session.get("liste", []))
    if mekan_id in liste:
        liste.remove(mekan_id)
        ekli = False
    else:
        liste = (liste + [mekan_id])[-MAKS_LISTE:]
        ekli = True
    session["liste"] = liste
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ekli": ekli, "adet": len(liste)})
    return redirect(request.referrer or url_for(".gezi_listesi"))


@bp.route("/listem")
def gezi_listesi():
    d = depo()
    idler = session.get("liste", [])
    gruplar = []
    for sehir_id in sorted({m["sehir_id"] for m in d.mekanlar(idler)}):
        sehir = d.sehir_id(sehir_id)
        mekanlar = [m for m in _sehir_mekanlari(sehir) if m["id"] in idler]
        mekanlar.sort(key=lambda m: idler.index(m["id"]))
        if request.args.get("rota") == "1":
            mekanlar = rota_sirala(mekanlar)
        duraklar = [f"{m['lat']},{m['lng']}" for m in mekanlar]
        gmaps = None
        km = rota_uzunlugu(mekanlar)
        if len(duraklar) >= 2:
            # 4 km'den uzun rotalar yürüyerek mantıklı değil
            gmaps = (f"https://www.google.com/maps/dir/?api=1&travelmode={'walking' if km <= 4 else 'driving'}"
                     f"&origin={duraklar[0]}&destination={duraklar[-1]}")
            if len(duraklar) > 2:
                gmaps += "&waypoints=" + "|".join(duraklar[1:-1][:8])
        gruplar.append({"sehir": sehir, "mekanlar": mekanlar, "gmaps": gmaps, "km": km,
                        "harita": _json({"merkez": [sehir["lat"], sehir["lng"]], "ref": None,
                                         "rota": True, "noktalar": _harita_noktalari(mekanlar)})})
    return render_template("listem.html", gruplar=gruplar, harita_modu=_harita_modu(),
                           rota=request.args.get("rota") == "1")


# ------------------------------------------------------------------ puan ayarları
@bp.post("/ayarlar/puan")
def puan_ayarla():
    if request.form.get("sifirla"):
        session.pop("agirlik", None)
    else:
        ham = {k: request.form.get(k) for k in list(VARSAYILAN_AGIRLIK) + ["google"]}
        agirlik, google_payi = agirliklari_duzelt(ham)
        session["agirlik"] = {**agirlik, "google": google_payi}
    hedef = request.form.get("geri") or ""
    # Sadece site içi adreslere dön (açık yönlendirme açığı olmasın)
    if not hedef.startswith("/") or hedef.startswith(("//", "/\\")):
        hedef = url_for(".index")
    return redirect(hedef)


@bp.app_errorhandler(404)
def bulunamadi(_e):
    return render_template("hata.html", baslik="Sayfa bulunamadı",
                           mesaj="Aradığınız sayfa ya da mekan yok. Şehir seçerek baştan başlayın."), 404
