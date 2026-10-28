"""Uzun süren işleri (şehir tarama, menü okuma) arka planda çalıştırır.

Basitlik için iş parçacığı (thread) kullanılır; ilerleme veritabanına yazılır ve sayfa
bunu birkaç saniyede bir sorgular. Üretimde Celery/RQ gibi bir kuyruğa taşınabilir.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from .db import Depo, baglan
from .metin import simdi_iso

log = logging.getLogger(__name__)


def baslat(app, tur: str, baslik: str, fonksiyon, *args) -> int:
    yol = app.config["VERITABANI"]
    conn = baglan(yol)
    depo = Depo(conn)
    mevcut = depo.calisan_is(baslik)
    if mevcut:
        conn.close()
        return mevcut["id"]
    is_id = depo.is_olustur(tur, baslik)
    conn.close()
    cfg = dict(app.config)

    def calis():
        c = baglan(yol)
        d = Depo(c)
        d.is_guncelle(is_id, durum="calisiyor")

        def ilerleme(yuzde, mesaj):
            d.is_guncelle(is_id, ilerleme=int(max(0, min(100, yuzde))), mesaj=mesaj,
                          log_ekle=f"{datetime.now():%H:%M:%S}  {mesaj}")

        try:
            sonuc_url = fonksiyon(cfg, d, ilerleme, *args)
            d.is_guncelle(is_id, durum="bitti", ilerleme=100, sonuc_url=sonuc_url,
                          bitis=simdi_iso())
        except Exception as e:  # kullanıcıya gösterilecek
            log.exception("İş başarısız: %s", baslik)
            d.is_guncelle(is_id, durum="hata", mesaj=str(e), bitis=simdi_iso(),
                          log_ekle=f"HATA: {e}")
        finally:
            c.close()

    if app.config.get("ISLER_SENKRON"):
        calis()
    else:
        threading.Thread(target=calis, daemon=True, name=f"is-{is_id}").start()
    return is_id
