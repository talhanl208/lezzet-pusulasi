"""SQLite veri katmanı. Her istek/iş parçacığı kendi bağlantısını açar."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3

from .metin import simdi_iso

SEMA = """
CREATE TABLE IF NOT EXISTS sehir (
    id INTEGER PRIMARY KEY,
    plaka INTEGER UNIQUE NOT NULL,
    ad TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    yaricap_km REAL NOT NULL,
    son_tarama TEXT,
    kaynak TEXT
);
CREATE TABLE IF NOT EXISTS mekan (
    id INTEGER PRIMARY KEY,
    sehir_id INTEGER NOT NULL REFERENCES sehir(id) ON DELETE CASCADE,
    kaynak TEXT NOT NULL,
    place_id TEXT UNIQUE NOT NULL,
    ad TEXT NOT NULL,
    adres TEXT,
    ilce TEXT,
    lat REAL,
    lng REAL,
    google_puan REAL,
    yorum_sayisi INTEGER DEFAULT 0,
    fiyat_seviyesi INTEGER,
    fiyat_min INTEGER,
    fiyat_max INTEGER,
    kategori TEXT,
    turler TEXT,
    birincil_tur TEXT,
    birincil_tur_adi TEXT,
    telefon TEXT,
    web TEXT,
    maps_url TEXT,
    calisma_saatleri TEXT,
    saat_periyotlari TEXT,
    ozellikler TEXT,
    google_ozet TEXT,
    google_ozet_aciklama TEXT,
    isletme_durumu TEXT,
    analiz TEXT,
    menu TEXT,
    derin_analiz_tarihi TEXT,
    pusula_puani REAL,
    olusturma TEXT,
    guncelleme TEXT
);
CREATE INDEX IF NOT EXISTS ix_mekan_sehir ON mekan(sehir_id);
CREATE TABLE IF NOT EXISTS yorum (
    id INTEGER PRIMARY KEY,
    mekan_id INTEGER NOT NULL REFERENCES mekan(id) ON DELETE CASCADE,
    kaynak TEXT NOT NULL,
    kaynak_id TEXT NOT NULL,
    yazar TEXT,
    yazar_url TEXT,
    yazar_foto TEXT,
    puan INTEGER,
    metin TEXT,
    tarih TEXT,
    goreli_tarih TEXT,
    dil TEXT,
    UNIQUE (mekan_id, kaynak_id)
);
CREATE INDEX IF NOT EXISTS ix_yorum_mekan ON yorum(mekan_id);
CREATE TABLE IF NOT EXISTS foto (
    id INTEGER PRIMARY KEY,
    mekan_id INTEGER NOT NULL REFERENCES mekan(id) ON DELETE CASCADE,
    kaynak TEXT NOT NULL,
    ref TEXT NOT NULL,
    genislik INTEGER,
    yukseklik INTEGER,
    yazar TEXT,
    yazar_url TEXT,
    kategori TEXT,
    menu_mu INTEGER,
    yukleme_tarihi TEXT,
    uri_onbellek TEXT,
    uri_tarih TEXT,
    sira INTEGER DEFAULT 0,
    UNIQUE (mekan_id, ref)
);
CREATE INDEX IF NOT EXISTS ix_foto_mekan ON foto(mekan_id);
CREATE TABLE IF NOT EXISTS api_sayac (
    gun TEXT NOT NULL,
    servis TEXT NOT NULL,
    adet INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (gun, servis)
);
CREATE TABLE IF NOT EXISTS is_kaydi (
    id INTEGER PRIMARY KEY,
    tur TEXT NOT NULL,
    baslik TEXT,
    durum TEXT NOT NULL DEFAULT 'bekliyor',
    ilerleme INTEGER DEFAULT 0,
    mesaj TEXT DEFAULT '',
    log TEXT DEFAULT '',
    sonuc_url TEXT,
    olusturma TEXT,
    bitis TEXT
);
"""

_JSON_ALANLAR = ("turler", "calisma_saatleri", "saat_periyotlari", "ozellikler", "analiz", "menu")


def baglan(yol: str) -> sqlite3.Connection:
    if yol != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
    conn = sqlite3.connect(yol, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    if yol != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def sema_kur(conn: sqlite3.Connection) -> None:
    conn.executescript(SEMA)
    conn.commit()


def _json(deger):
    return None if deger is None else json.dumps(deger, ensure_ascii=False)


def _coz(deger, varsayilan=None):
    if deger in (None, ""):
        return varsayilan
    try:
        return json.loads(deger)
    except (TypeError, ValueError):
        return varsayilan


def yorum_kimligi(yazar: str, metin: str, tarih: str = "") -> str:
    ham = f"{yazar}|{(metin or '')[:120]}|{(tarih or '')[:10]}"
    return hashlib.sha1(ham.encode("utf-8")).hexdigest()[:20]


class Depo:
    """Uygulamanın tüm okuma/yazma işlemleri burada."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---------- şehir ----------
    def sehir_kaydet(self, il: dict) -> dict:
        self.conn.execute(
            """INSERT INTO sehir (plaka, ad, slug, lat, lng, yaricap_km)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(plaka) DO UPDATE SET ad=excluded.ad, slug=excluded.slug,
                   lat=excluded.lat, lng=excluded.lng, yaricap_km=excluded.yaricap_km""",
            (il["plaka"], il["ad"], il["slug"], il["lat"], il["lng"], il["yaricap_km"]))
        self.conn.commit()
        return self.sehir_slug(il["slug"])

    def sehir_slug(self, slug: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM sehir WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None

    def sehir_id(self, sehir_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM sehir WHERE id = ?", (sehir_id,)).fetchone()
        return dict(row) if row else None

    def taranmis_sehirler(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT s.*, COUNT(m.id) AS mekan_sayisi FROM sehir s
               JOIN mekan m ON m.sehir_id = s.id
               GROUP BY s.id ORDER BY s.son_tarama DESC""").fetchall()
        return [dict(r) for r in rows]

    def sehir_tarandi(self, sehir_id: int, kaynak: str) -> None:
        self.conn.execute("UPDATE sehir SET son_tarama = ?, kaynak = ? WHERE id = ?",
                          (simdi_iso(), kaynak, sehir_id))
        self.conn.commit()

    # ---------- mekan ----------
    _MEKAN_ALANLARI = ("ad", "adres", "ilce", "lat", "lng", "google_puan", "yorum_sayisi",
                       "fiyat_seviyesi", "fiyat_min", "fiyat_max", "kategori", "turler",
                       "birincil_tur", "birincil_tur_adi", "telefon", "web", "maps_url",
                       "calisma_saatleri", "saat_periyotlari", "ozellikler", "google_ozet",
                       "google_ozet_aciklama", "isletme_durumu")

    def mekan_kaydet(self, sehir_id: int, kaynak: str, kayit: dict) -> int:
        """Mekanı ekler ya da günceller; analiz ve menü bilgisi korunur."""
        degerler = []
        for alan in self._MEKAN_ALANLARI:
            d = kayit.get(alan)
            degerler.append(_json(d) if alan in _JSON_ALANLAR else d)
        zaman = simdi_iso()
        guncelle = ", ".join(f"{a}=excluded.{a}" for a in self._MEKAN_ALANLARI)
        self.conn.execute(
            f"""INSERT INTO mekan (sehir_id, kaynak, place_id, {", ".join(self._MEKAN_ALANLARI)},
                    olusturma, guncelleme)
                VALUES (?, ?, ?, {", ".join("?" * len(self._MEKAN_ALANLARI))}, ?, ?)
                ON CONFLICT(place_id) DO UPDATE SET {guncelle}, guncelleme=excluded.guncelleme,
                    sehir_id=excluded.sehir_id""",
            (sehir_id, kaynak, kayit["place_id"], *degerler, zaman, zaman))
        mekan_id = self.conn.execute("SELECT id FROM mekan WHERE place_id = ?",
                                     (kayit["place_id"],)).fetchone()["id"]
        for yorum in kayit.get("yorumlar", []):
            self.yorum_ekle(mekan_id, yorum.get("kaynak", kaynak), yorum, commit=False)
        for sira, foto in enumerate(kayit.get("fotolar", [])):
            self.foto_ekle(mekan_id, foto.get("kaynak", kaynak), foto, sira, commit=False)
        self.conn.commit()
        return mekan_id

    def _mekan_coz(self, row) -> dict:
        m = dict(row)
        for alan in _JSON_ALANLAR:
            m[alan] = _coz(m.get(alan), [] if alan in ("turler", "calisma_saatleri",
                                                        "saat_periyotlari") else None)
        m["ozellikler"] = m["ozellikler"] or {}
        return m

    def mekan(self, mekan_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM mekan WHERE id = ?", (mekan_id,)).fetchone()
        return self._mekan_coz(row) if row else None

    def mekanlar(self, ids) -> list[dict]:
        ids = [int(i) for i in ids]
        if not ids:
            return []
        rows = self.conn.execute(
            f"SELECT * FROM mekan WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()
        sozluk = {r["id"]: self._mekan_coz(r) for r in rows}
        return [sozluk[i] for i in ids if i in sozluk]

    def sehir_mekanlari(self, sehir_id: int) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM mekan WHERE sehir_id = ?", (sehir_id,)).fetchall()
        return [self._mekan_coz(r) for r in rows]

    def analiz_kaydet(self, mekan_id: int, analiz: dict) -> None:
        self.conn.execute("UPDATE mekan SET analiz = ? WHERE id = ?", (_json(analiz), mekan_id))
        self.conn.commit()

    def menu_kaydet(self, mekan_id: int, menu: dict) -> None:
        self.conn.execute("UPDATE mekan SET menu = ? WHERE id = ?", (_json(menu), mekan_id))
        self.conn.commit()

    def puan_kaydet(self, mekan_id: int, puan: float | None) -> None:
        self.conn.execute("UPDATE mekan SET pusula_puani = ? WHERE id = ?", (puan, mekan_id))
        self.conn.commit()

    def derin_analiz_isaretle(self, mekan_id: int) -> None:
        self.conn.execute("UPDATE mekan SET derin_analiz_tarihi = ? WHERE id = ?",
                          (simdi_iso(), mekan_id))
        self.conn.commit()

    # ---------- yorum ----------
    def yorum_ekle(self, mekan_id: int, kaynak: str, y: dict, commit: bool = True) -> None:
        kimlik = y.get("kaynak_id") or yorum_kimligi(y.get("yazar", ""), y.get("metin", ""),
                                                    y.get("tarih", ""))
        self.conn.execute(
            """INSERT OR IGNORE INTO yorum (mekan_id, kaynak, kaynak_id, yazar, yazar_url,
                   yazar_foto, puan, metin, tarih, goreli_tarih, dil)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mekan_id, kaynak, kimlik, y.get("yazar"), y.get("yazar_url"), y.get("yazar_foto"),
             y.get("puan"), y.get("metin"), y.get("tarih"), y.get("goreli_tarih"), y.get("dil")))
        if commit:
            self.conn.commit()

    def yorumlar(self, mekan_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM yorum WHERE mekan_id = ? ORDER BY tarih DESC", (mekan_id,)).fetchall()
        return [dict(r) for r in rows]

    def sehir_yorumlari(self, sehir_id: int) -> dict[int, list[dict]]:
        rows = self.conn.execute(
            """SELECT y.* FROM yorum y JOIN mekan m ON m.id = y.mekan_id
               WHERE m.sehir_id = ? ORDER BY y.tarih DESC""", (sehir_id,)).fetchall()
        sonuc: dict[int, list[dict]] = {}
        for r in rows:
            sonuc.setdefault(r["mekan_id"], []).append(dict(r))
        return sonuc

    # ---------- foto ----------
    def foto_ekle(self, mekan_id: int, kaynak: str, f: dict, sira: int = 0,
                  commit: bool = True) -> None:
        self.conn.execute(
            """INSERT INTO foto (mekan_id, kaynak, ref, genislik, yukseklik, yazar, yazar_url,
                   kategori, menu_mu, yukleme_tarihi, sira)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mekan_id, ref) DO UPDATE SET sira = excluded.sira,
                   yukleme_tarihi = COALESCE(excluded.yukleme_tarihi, foto.yukleme_tarihi),
                   menu_mu = COALESCE(excluded.menu_mu, foto.menu_mu),
                   kategori = COALESCE(excluded.kategori, foto.kategori)""",
            (mekan_id, kaynak, f["ref"], f.get("genislik"), f.get("yukseklik"), f.get("yazar"),
             f.get("yazar_url"), f.get("kategori"), f.get("menu_mu"), f.get("yukleme_tarihi"),
             f.get("sira", sira)))
        if commit:
            self.conn.commit()

    def fotolar(self, mekan_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM foto WHERE mekan_id = ? ORDER BY sira, id", (mekan_id,)).fetchall()
        return [dict(r) for r in rows]

    def foto(self, foto_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM foto WHERE id = ?", (foto_id,)).fetchone()
        return dict(row) if row else None

    def kapak_fotolari(self, sehir_id: int) -> dict[int, int]:
        """Her mekan için menü olmayan ilk fotoğrafın id'si."""
        rows = self.conn.execute(
            """SELECT f.mekan_id, f.id FROM foto f JOIN mekan m ON m.id = f.mekan_id
               WHERE m.sehir_id = ? AND COALESCE(f.menu_mu, 0) = 0
               ORDER BY f.mekan_id, f.sira, f.id""", (sehir_id,)).fetchall()
        sonuc: dict[int, int] = {}
        for r in rows:
            sonuc.setdefault(r["mekan_id"], r["id"])
        return sonuc

    def foto_menu_isaretle(self, foto_id: int, menu_mu: bool) -> None:
        self.conn.execute("UPDATE foto SET menu_mu = ? WHERE id = ?", (int(menu_mu), foto_id))
        self.conn.commit()

    def foto_uri_kaydet(self, foto_id: int, uri: str) -> None:
        self.conn.execute("UPDATE foto SET uri_onbellek = ?, uri_tarih = ? WHERE id = ?",
                          (uri, simdi_iso(), foto_id))
        self.conn.commit()

    # ---------- günlük API sayacı ----------
    def sayac_artir(self, servis: str, limit: int) -> bool:
        """Bugünkü sayaç limitin altındaysa 1 artırır ve True döner; doluysa False."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        gun = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
        self.conn.execute("INSERT OR IGNORE INTO api_sayac (gun, servis, adet) VALUES (?, ?, 0)",
                          (gun, servis))
        cur = self.conn.execute(
            "UPDATE api_sayac SET adet = adet + 1 WHERE gun = ? AND servis = ? AND adet < ?",
            (gun, servis, limit))
        self.conn.commit()
        return cur.rowcount == 1

    def bugunku_kullanim(self) -> dict[str, int]:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        gun = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
        rows = self.conn.execute("SELECT servis, adet FROM api_sayac WHERE gun = ?", (gun,)).fetchall()
        return {r["servis"]: r["adet"] for r in rows}

    # ---------- arka plan işleri ----------
    def is_olustur(self, tur: str, baslik: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO is_kaydi (tur, baslik, durum, olusturma) VALUES (?, ?, 'bekliyor', ?)",
            (tur, baslik, simdi_iso()))
        self.conn.commit()
        return cur.lastrowid

    def is_guncelle(self, is_id: int, **alanlar) -> None:
        if "log_ekle" in alanlar:
            satir = alanlar.pop("log_ekle")
            self.conn.execute("UPDATE is_kaydi SET log = COALESCE(log, '') || ? WHERE id = ?",
                              (satir + "\n", is_id))
        if alanlar:
            kume = ", ".join(f"{k} = ?" for k in alanlar)
            self.conn.execute(f"UPDATE is_kaydi SET {kume} WHERE id = ?",
                              (*alanlar.values(), is_id))
        self.conn.commit()

    def is_kaydi(self, is_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM is_kaydi WHERE id = ?", (is_id,)).fetchone()
        return dict(row) if row else None

    def calisan_is(self, baslik: str) -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM is_kaydi WHERE baslik = ? AND durum IN ('bekliyor', 'calisiyor')
               ORDER BY id DESC LIMIT 1""", (baslik,)).fetchone()
        return dict(row) if row else None
