"""Lezzet Pusulası — Türkiye'de gittiğin şehirdeki restoranları tek ekranda karşılaştır."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, g

from .db import Depo, baglan, sema_kur

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bool(deger, varsayilan=False) -> bool:
    if deger is None or deger == "":
        return varsayilan
    return str(deger).strip().lower() in ("1", "true", "evet", "yes", "on")


def ayarlari_oku() -> dict:
    load_dotenv(os.path.join(KOK, ".env"))
    google = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    arka_plan = _bool(os.getenv("ARKA_PLAN_ISLERI"), varsayilan=True)
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY") or secrets.token_hex(32),
        "VERITABANI": os.getenv("VERITABANI") or os.path.join(KOK, "instance", "pusula.sqlite3"),
        "GOOGLE_PLACES_API_KEY": google,
        "GOOGLE_MAPS_JS_KEY": os.getenv("GOOGLE_MAPS_JS_KEY", "").strip(),
        "GOOGLE_MAP_ID": os.getenv("GOOGLE_MAP_ID", "DEMO_MAP_ID").strip(),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "").strip(),
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL", "claude-haiku-5-5").strip(),
        "SERPAPI_API_KEY": os.getenv("SERPAPI_API_KEY", "").strip(),
        # Google anahtarı yoksa otomatik demo modu
        "DEMO": _bool(os.getenv("DEMO_MODU"), varsayilan=not google),
        "VARSAYILAN_HEDEF": int(os.getenv("VARSAYILAN_HEDEF", "50")),
        "MENU_TARAMA_LIMITI": int(os.getenv("MENU_TARAMA_LIMITI", "8")),
        "DERIN_ANALIZ_LIMITI": int(os.getenv("DERIN_ANALIZ_LIMITI", "0")),
        "DERIN_YORUM_ADEDI": int(os.getenv("DERIN_YORUM_ADEDI", "30")),
        "YENILEME_GUN": int(os.getenv("YENILEME_GUN", "30")),
        "FOTO_URI_SAAT": int(os.getenv("FOTO_URI_SAAT", "24")),
        # Fatura güvenliği: Google'a günde en fazla bu kadar istek gönderilir
        "GUNLUK_ARAMA_LIMITI": int(os.getenv("GUNLUK_ARAMA_LIMITI", "200")),
        "GUNLUK_FOTO_LIMITI": int(os.getenv("GUNLUK_FOTO_LIMITI", "300")),
        # İnternete açarken mutlaka doldurun: boşsa giriş istenmez
        "APP_SIFRESI": os.getenv("APP_SIFRESI", "").strip(),
        # PythonAnywhere gibi thread desteklemeyen sunucularda 0 yapın
        "ARKA_PLAN_ISLERI": arka_plan,
        # Tarama sırasında tüm mekanları Claude ile analiz et (0 ise mekan açılınca analiz edilir)
        "CLAUDE_TOPLU_ANALIZ": _bool(os.getenv("CLAUDE_TOPLU_ANALIZ"), varsayilan=arka_plan),
        "ISLER_SENKRON": not arka_plan,
        "SESSION_COOKIE_SECURE": _bool(os.getenv("HTTPS")),
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_HTTPONLY": True,
        "PERMANENT_SESSION_LIFETIME": timedelta(days=30),
    }


def create_app(ayar: dict | None = None) -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = Flask(__name__, instance_path=os.path.join(KOK, "instance"))
    app.config.update(ayarlari_oku())
    if ayar:
        app.config.update(ayar)
    app.config["JSON_AS_ASCII"] = False

    conn = baglan(app.config["VERITABANI"])
    sema_kur(conn)
    conn.close()

    @app.teardown_appcontext
    def _kapat(_hata):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    from . import web
    app.register_blueprint(web.bp)
    web.sablon_ayarlari(app)
    _komutlar(app)
    return app


def _komutlar(app: Flask) -> None:
    import click

    @app.cli.command("tara")
    @click.argument("sehir")
    @click.option("--hedef", default=50, help="Kaç mekan toplanacak")
    @click.option("--bolge", default="", help="Semt/ilçe (ör. Kadıköy)")
    def tara_komutu(sehir, hedef, bolge):
        """Bir şehri terminalden tarar: flask --app app tara konya"""
        from .iller import il_bul
        from .tarama import sehir_tara
        il = il_bul(sehir)
        if not il:
            raise click.ClickException(f"Şehir bulunamadı: {sehir}")
        conn = baglan(app.config["VERITABANI"])
        try:
            yol = sehir_tara(dict(app.config), Depo(conn), lambda y, m: click.echo(f"[%{int(y):3d}] {m}"),
                             il, hedef, bolge)
        finally:
            conn.close()
        click.echo(f"Bitti: http://127.0.0.1:5000{yol}")


def depo() -> Depo:
    from flask import current_app
    if "db" not in g:
        g.db = baglan(current_app.config["VERITABANI"])
    return Depo(g.db)
