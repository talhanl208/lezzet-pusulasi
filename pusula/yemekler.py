"""Yorumlarda ve menülerde aranan yemek sözlüğü (görünen ad, aksansız kalıplar)."""
from __future__ import annotations

import re

from .metin import katla

YEMEKLER = [
    ("Adana kebap", ["adana"]), ("Urfa kebap", ["urfa keba", "urfa kebap"]),
    ("İskender", ["iskender"]), ("Beyti", ["beyti"]), ("Ali nazik", ["ali nazik"]),
    ("Kuzu şiş", ["kuzu sis"]), ("Tavuk şiş", ["tavuk sis"]), ("Çöp şiş", ["cop sis"]),
    ("Pirzola", ["pirzola"]), ("Kuzu tandır", ["tandir"]), ("Ciğer", ["ciger"]),
    ("İnegöl köfte", ["inegol"]), ("Köfte", ["kofte", "koftesi"]),
    ("Lahmacun", ["lahmacun"]), ("Pide", ["pide"]), ("Etli ekmek", ["etli ekmek"]),
    ("Fırın kebabı", ["firin kebab"]), ("Döner", ["doner"]), ("Dürüm", ["=durum", "durumcu"]),
    ("Tantuni", ["tantuni"]), ("Kokoreç", ["kokorec"]), ("Çiğ köfte", ["cig kofte"]),
    ("Mantı", ["manti"]), ("Mercimek çorbası", ["mercimek"]), ("İşkembe", ["iskembe"]),
    ("Kelle paça", ["kelle paca", "paca corba"]), ("Kuru fasulye", ["kuru fasulye", "kurufasulye"]),
    ("Pilav", ["pilav"]), ("Karnıyarık", ["karniyarik"]), ("Hünkar beğendi", ["hunkar"]),
    ("Kaburga", ["kaburga"]), ("Testi kebabı", ["testi keba"]), ("Cağ kebabı", ["cag keba"]),
    ("Beyran", ["beyran"]), ("İçli köfte", ["icli kofte"]), ("Yaprak sarma", ["sarma"]),
    ("Hamsi", ["hamsi"]), ("Levrek", ["levrek"]), ("Çipura", ["cipura"]),
    ("Midye", ["midye"]), ("Kalamar", ["kalamar"]), ("Balık ekmek", ["balik ekmek"]),
    ("Menemen", ["menemen"]), ("Kuymak", ["kuymak", "muhlama"]), ("Gözleme", ["gozleme"]),
    ("Börek", ["borek"]), ("Serpme kahvaltı", ["serpme"]), ("Simit", ["simit"]),
    ("Baklava", ["baklava"]), ("Künefe", ["kunefe"]), ("Katmer", ["katmer"]),
    ("Sütlaç", ["sutlac"]), ("Kazandibi", ["kazandibi"]), ("Dondurma", ["dondurma"]),
    ("Hamburger", ["burger", "cheeseburger", "hamburger"]), ("Pizza", ["pizza"]), ("Makarna", ["makarna", "spagetti", "penne"]),
    ("Steak", ["steak", "biftek", "antrikot"]), ("Sushi", ["sushi"]), ("Kumru", ["kumru"]),
    ("Boyoz", ["boyoz"]), ("Humus", ["humus"]), ("Mezeler", ["meze"]),
    ("Kumpir", ["kumpir"]), ("Waffle", ["waffle"]), ("Tiramisu", ["tiramisu"]),
    ("Cheesecake", ["cheesecake"]), ("Sufle", ["sufle"]), ("Türk kahvesi", ["turk kahve"]),
    ("Tost", ["tost"]), ("Ayran", ["ayran"]), ("Şalgam", ["salgam"]),
]


def _eslesir(kalip: str, metin: str) -> bool:
    # "=durum" → yalnızca tam kelime ("dürüm" ile "durum" aynı yazılıyor)
    if kalip.startswith("="):
        return f" {kalip[1:]} " in metin
    # Kelime başında eşleşme: "romantik" içindeki "manti" sayılmasın
    return f" {kalip}" in metin


def yemekleri_bul(metin: str) -> list[str]:
    """Metinde geçen yemeklerin görünen adları (tekrarsız, sırayla)."""
    k = " " + re.sub(r"[^a-z0-9]+", " ", katla(metin)) + " "
    bulunan = []
    for ad, kaliplar in YEMEKLER:
        if any(_eslesir(kalip, k) for kalip in kaliplar):
            bulunan.append(ad)
    # 'Köfte' genel, daha özel bir köfte bulunduysa tekrar sayma
    if "Köfte" in bulunan and {"İnegöl köfte", "Çiğ köfte", "İçli köfte"} & set(bulunan):
        bulunan.remove("Köfte")
    return bulunan
