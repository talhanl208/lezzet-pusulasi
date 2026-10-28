"""Mekanları Türkiye'ye özgü kategorilere ayırır (isim + Google türleri)."""
from __future__ import annotations

from .metin import katla

# kod: (görünen ad, emoji)
KATEGORILER = {
    "kebap": ("Kebap & Köfte", "🍢"),
    "esnaf": ("Esnaf lokantası", "🍲"),
    "sokak": ("Döner & sokak lezzeti", "🌯"),
    "pide": ("Pide & lahmacun", "🫓"),
    "fastfood": ("Fast food", "🍔"),
    "pizza": ("Pizza & İtalyan", "🍕"),
    "balik": ("Balık & deniz ürünleri", "🐟"),
    "kahvalti": ("Kahvaltı & börek", "🍳"),
    "kafe": ("Kafe", "☕"),
    "tatli": ("Tatlı & pastane", "🍰"),
    "meyhane": ("Meyhane & bar", "🍷"),
    "dunya": ("Dünya mutfağı", "🍜"),
    "fine": ("Fine dining", "✨"),
    "restoran": ("Restoran", "🍽️"),
}

# İsimde geçen kelimeler (aksansız). Sıra önemli: ilk eşleşen kazanır.
_ISIM_KURALLARI = [
    ("tatli", ["baklava", "kunefe", "tatli", "pastane", "dondurma", "muhallebi",
               "sutlac", "katmer", "lokum", "kadayif", "patisserie"]),
    ("balik", ["balik", "deniz urun", "midye", "hamsi", "levrek", "fish", "seafood"]),
    ("kahvalti", ["kahvalti", "serpme", "gozleme", "borek", "simit", "pogaca", "kahvalt", "breakfast"]),
    ("sokak", ["doner", "durum", "tantuni", "kokorec", "cig kofte", "bufe", "tost", "kumru",
               "sogus", "ciger"]),
    ("pide", ["pide", "lahmacun", "etli ekmek"]),
    ("kebap", ["kebap", "kebab", "ocakbasi", "kofte", "izgara", "mangal", "beyran", "cag "]),
    ("esnaf", ["lokanta", "ev yemek", "esnaf", "sulu yemek", "tencere", "corba", "iskembe",
               "kelle", "pace", "manti"]),
    ("meyhane", ["meyhane", "raki", " bar", "pub", "bira", "sarap", "wine", "brew"]),
    ("pizza", ["pizza", "pizzeria", "trattoria", "pasta bar", "italyan", "italian"]),
    ("fastfood", ["burger", "fast food", "chicken", "wings", "hot dog", "sandwich"]),
    ("dunya", ["sushi", "ramen", "noodle", "wok", "cin ", "chinese", "japon", "kore", "thai",
               "hint", "indian", "mexican", "meksika", "asya", "asian", "taco", "dim sum"]),
    ("kafe", ["cafe", "kafe", "kahve", "coffee", "cay bahcesi", "kiraathane", "roastery"]),
]

_TUR_KURALLARI = {
    "fine_dining_restaurant": "fine",
    "fast_food_restaurant": "fastfood", "hamburger_restaurant": "fastfood",
    "sandwich_shop": "fastfood", "chicken_restaurant": "fastfood", "meal_takeaway": "fastfood",
    "pizza_restaurant": "pizza", "italian_restaurant": "pizza",
    "seafood_restaurant": "balik", "fish_and_chips_restaurant": "balik",
    "breakfast_restaurant": "kahvalti", "brunch_restaurant": "kahvalti",
    "cafe": "kafe", "coffee_shop": "kafe", "tea_house": "kafe", "cat_cafe": "kafe",
    "bakery": "tatli", "dessert_shop": "tatli", "dessert_restaurant": "tatli",
    "ice_cream_shop": "tatli", "confectionery": "tatli", "pastry_shop": "tatli",
    "candy_store": "tatli", "chocolate_shop": "tatli", "donut_shop": "tatli",
    "bar": "meyhane", "pub": "meyhane", "wine_bar": "meyhane", "bar_and_grill": "meyhane",
    "cocktail_bar": "meyhane", "brewery": "meyhane",
    "kebab_shop": "kebap", "barbecue_restaurant": "kebap",
}
_DUNYA_SONEKLERI = ("japanese", "sushi", "chinese", "korean", "thai", "indian", "mexican",
                    "asian", "ramen", "vietnamese", "indonesian", "lebanese", "spanish",
                    "french", "greek", "american", "brazilian", "afghani", "african")

# Yemek mekanı sayılan Google türleri (otel, market vb. elenir)
_YEMEK_TURLERI = {"restaurant", "food", "cafe", "bakery", "bar", "meal_takeaway",
                  "meal_delivery", "coffee_shop", "pub", "wine_bar", "tea_house",
                  "dessert_shop", "ice_cream_shop", "confectionery", "food_court",
                  "sandwich_shop", "deli", "diner", "pastry_shop", "cafeteria"}


def yemek_mekani_mi(turler) -> bool:
    turler = set(turler or [])
    if turler & _YEMEK_TURLERI:
        return True
    return any(t.endswith("_restaurant") or (t.endswith("_shop") and "food" in t) for t in turler)


def kategori_belirle(ad: str, turler=None, birincil_tur: str = "",
                     fiyat_seviyesi: int | None = None) -> str:
    isim = f" {katla(ad)} "
    for kod, kelimeler in _ISIM_KURALLARI:
        if any(k in isim for k in kelimeler):
            return kod
    sirali = [birincil_tur] + list(turler or []) if birincil_tur else list(turler or [])
    for tur in sirali:
        if tur in _TUR_KURALLARI:
            return _TUR_KURALLARI[tur]
        if tur.endswith("_restaurant") and tur.startswith(_DUNYA_SONEKLERI):
            return "dunya"
    if fiyat_seviyesi == 4:
        return "fine"
    return "restoran"


def kategori_adi(kod: str) -> str:
    return KATEGORILER.get(kod, KATEGORILER["restoran"])[0]


def kategori_emoji(kod: str) -> str:
    return KATEGORILER.get(kod, KATEGORILER["restoran"])[1]
