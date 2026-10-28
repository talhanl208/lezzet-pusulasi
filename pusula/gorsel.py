"""Demo modunda gerçek fotoğraf yerine çizilen basit SVG görseller."""
from __future__ import annotations

import random
from html import escape

# kategori → (zemin, vurgu)
RENKLER = {
    "kebap": ("#7a2a1d", "#e0773a"), "esnaf": ("#5b4a2e", "#d9a441"),
    "sokak": ("#6b3a1f", "#e8a23a"), "pide": ("#7a4a1d", "#e3a857"),
    "fastfood": ("#3d2a5c", "#f2b134"), "pizza": ("#6e2420", "#e9c46a"),
    "balik": ("#123c5a", "#5fb3c9"), "kahvalti": ("#5c4a1a", "#f4d35e"),
    "kafe": ("#3b2a22", "#c08552"), "tatli": ("#5a2440", "#e79fbd"),
    "meyhane": ("#1d3b3a", "#9bc4a8"), "dunya": ("#3a1f3d", "#e05d5d"),
    "fine": ("#1c2433", "#c9b47c"), "restoran": ("#24365e", "#d2452e"),
}


def _yemek(r: random.Random, zemin: str, vurgu: str) -> str:
    parcalar = []
    for _ in range(r.randint(4, 7)):
        x, y = r.randint(150, 250), r.randint(110, 190)
        rx, ry = r.randint(14, 38), r.randint(10, 26)
        renk = r.choice([vurgu, "#f1e3c8", "#8fae5d", "#c2452d", "#e9c46a"])
        parcalar.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{renk}" '
                        f'opacity="0.92" transform="rotate({r.randint(0, 180)} {x} {y})"/>')
    return (f'<rect width="400" height="300" fill="{zemin}"/>'
            f'<circle cx="200" cy="150" r="118" fill="#000" opacity="0.18"/>'
            f'<circle cx="200" cy="148" r="112" fill="#f7f4ee"/>'
            f'<circle cx="200" cy="148" r="86" fill="#fffdf8" stroke="#e7e1d6" stroke-width="3"/>'
            + "".join(parcalar) +
            '<rect x="40" y="70" width="8" height="160" rx="4" fill="#d9d4ca"/>'
            '<rect x="352" y="70" width="8" height="160" rx="4" fill="#d9d4ca"/>')


def _mekan(r: random.Random, zemin: str, vurgu: str) -> str:
    kemerler = []
    for i in range(4):
        x = 30 + i * 90
        kemerler.append(f'<path d="M{x} 270 V120 a40 40 0 0 1 80 0 V270 Z" fill="#0d1726" opacity="0.55"/>'
                        f'<path d="M{x + 10} 270 V125 a30 30 0 0 1 60 0 V270 Z" fill="{vurgu}" opacity="0.35"/>')
    lambalar = "".join(f'<circle cx="{70 + i * 90}" cy="{r.randint(60, 80)}" r="9" fill="#ffd27a"/>'
                       f'<line x1="{70 + i * 90}" y1="0" x2="{70 + i * 90}" y2="55" stroke="#ffd27a" '
                       f'stroke-width="1.5"/>' for i in range(4))
    return (f'<rect width="400" height="300" fill="{zemin}"/>' + "".join(kemerler) + lambalar +
            '<rect y="270" width="400" height="30" fill="#0d1726" opacity="0.6"/>')


def _menu(mekan_adi: str, urunler: list[dict], tarih: str | None) -> str:
    satirlar = []
    for i, u in enumerate(urunler[:9]):
        y = 92 + i * 20
        fiyat = f"{int(u['fiyat'])} ₺" if u.get("fiyat") else "—"
        satirlar.append(
            f'<text x="62" y="{y}" font-size="12.5" fill="#2b2b2b">{escape(u["ad"][:28])}</text>'
            f'<line x1="62" y1="{y + 4}" x2="338" y2="{y + 4}" stroke="#c9bfae" stroke-dasharray="2 3"/>'
            f'<text x="338" y="{y}" font-size="12.5" fill="#2b2b2b" text-anchor="end" '
            f'font-weight="700">{fiyat}</text>')
    alt = f"Fiyatlar {escape(tarih)} tarihli" if tarih else ""
    return ('<rect width="400" height="300" fill="#3b3229"/>'
            '<rect x="40" y="22" width="320" height="262" rx="4" fill="#f6efe1" '
            'transform="rotate(-1.2 200 150)"/>'
            '<g transform="rotate(-1.2 200 150)" font-family="Georgia, serif">'
            f'<text x="200" y="58" font-size="17" text-anchor="middle" fill="#7a2a1d" '
            f'font-weight="700">{escape(mekan_adi[:30])}</text>'
            '<text x="200" y="74" font-size="10" text-anchor="middle" fill="#8a7b66">MENÜ</text>'
            + "".join(satirlar) +
            f'<text x="200" y="276" font-size="9" text-anchor="middle" fill="#8a7b66">{alt}</text>'
            '</g>')


def demo_svg(foto: dict, mekan: dict) -> str:
    r = random.Random(foto["id"] * 31 + 7)
    zemin, vurgu = RENKLER.get(mekan.get("kategori"), RENKLER["restoran"])
    tur = foto.get("kategori") or "yemek"
    if tur == "menu":
        menu = mekan.get("menu") or {}
        ic = _menu(mekan["ad"], menu.get("urunler") or [], (foto.get("yukleme_tarihi") or "")[:7])
    elif tur == "mekan":
        ic = _mekan(r, zemin, vurgu)
    else:
        ic = _yemek(r, zemin, vurgu)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" '
            'preserveAspectRatio="xMidYMid slice">' + ic +
            '<text x="388" y="292" font-size="10" text-anchor="end" fill="#fff" opacity="0.7" '
            'font-family="sans-serif">demo görsel</text></svg>')


def yer_tutucu_svg() -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            '<rect width="400" height="300" fill="#dfe6ee"/>'
            '<circle cx="200" cy="150" r="60" fill="none" stroke="#9aa9bc" stroke-width="6"/>'
            '<path d="M200 105 L212 150 L200 195 L188 150 Z" fill="#9aa9bc"/></svg>')
