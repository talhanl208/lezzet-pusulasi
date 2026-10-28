"""Türkiye'nin 81 ili: plaka, il merkezi koordinatı, tarama yarıçapı ve yöresel lezzetler."""
from __future__ import annotations

from .metin import katla, slugla

# (plaka, ad, enlem, boylam)
_ILLER = [
    (1, "Adana", 37.0000, 35.3213), (2, "Adıyaman", 37.7648, 38.2786),
    (3, "Afyonkarahisar", 38.7507, 30.5567), (4, "Ağrı", 39.7191, 43.0503),
    (5, "Amasya", 40.6499, 35.8353), (6, "Ankara", 39.9334, 32.8597),
    (7, "Antalya", 36.8969, 30.7133), (8, "Artvin", 41.1828, 41.8183),
    (9, "Aydın", 37.8560, 27.8416), (10, "Balıkesir", 39.6484, 27.8826),
    (11, "Bilecik", 40.1451, 29.9799), (12, "Bingöl", 38.8847, 40.4939),
    (13, "Bitlis", 38.4006, 42.1095), (14, "Bolu", 40.7392, 31.6089),
    (15, "Burdur", 37.7203, 30.2908), (16, "Bursa", 40.1885, 29.0610),
    (17, "Çanakkale", 40.1553, 26.4142), (18, "Çankırı", 40.6013, 33.6134),
    (19, "Çorum", 40.5506, 34.9556), (20, "Denizli", 37.7765, 29.0864),
    (21, "Diyarbakır", 37.9144, 40.2306), (22, "Edirne", 41.6818, 26.5623),
    (23, "Elazığ", 38.6810, 39.2264), (24, "Erzincan", 39.7500, 39.5000),
    (25, "Erzurum", 39.9000, 41.2700), (26, "Eskişehir", 39.7767, 30.5206),
    (27, "Gaziantep", 37.0662, 37.3833), (28, "Giresun", 40.9128, 38.3895),
    (29, "Gümüşhane", 40.4386, 39.5086), (30, "Hakkari", 37.5833, 43.7333),
    (31, "Hatay", 36.2021, 36.1600), (32, "Isparta", 37.7648, 30.5566),
    (33, "Mersin", 36.8000, 34.6333), (34, "İstanbul", 41.0082, 28.9784),
    (35, "İzmir", 38.4237, 27.1428), (36, "Kars", 40.6167, 43.1000),
    (37, "Kastamonu", 41.3887, 33.7827), (38, "Kayseri", 38.7312, 35.4787),
    (39, "Kırklareli", 41.7333, 27.2167), (40, "Kırşehir", 39.1425, 34.1709),
    (41, "Kocaeli", 40.8533, 29.8815), (42, "Konya", 37.8746, 32.4932),
    (43, "Kütahya", 39.4167, 29.9833), (44, "Malatya", 38.3552, 38.3095),
    (45, "Manisa", 38.6191, 27.4289), (46, "Kahramanmaraş", 37.5858, 36.9371),
    (47, "Mardin", 37.3212, 40.7245), (48, "Muğla", 37.2153, 28.3636),
    (49, "Muş", 38.9462, 41.7539), (50, "Nevşehir", 38.6939, 34.6857),
    (51, "Niğde", 37.9667, 34.6833), (52, "Ordu", 40.9839, 37.8764),
    (53, "Rize", 41.0201, 40.5234), (54, "Sakarya", 40.7569, 30.3783),
    (55, "Samsun", 41.2928, 36.3313), (56, "Siirt", 37.9333, 41.9500),
    (57, "Sinop", 42.0231, 35.1531), (58, "Sivas", 39.7477, 37.0179),
    (59, "Tekirdağ", 40.9833, 27.5167), (60, "Tokat", 40.3167, 36.5500),
    (61, "Trabzon", 41.0015, 39.7178), (62, "Tunceli", 39.1079, 39.5401),
    (63, "Şanlıurfa", 37.1591, 38.7969), (64, "Uşak", 38.6823, 29.4082),
    (65, "Van", 38.4891, 43.4089), (66, "Yozgat", 39.8181, 34.8147),
    (67, "Zonguldak", 41.4564, 31.7987), (68, "Aksaray", 38.3687, 34.0370),
    (69, "Bayburt", 40.2552, 40.2249), (70, "Karaman", 37.1759, 33.2287),
    (71, "Kırıkkale", 39.8468, 33.5153), (72, "Batman", 37.8812, 41.1351),
    (73, "Şırnak", 37.5164, 42.4611), (74, "Bartın", 41.6344, 32.3375),
    (75, "Ardahan", 41.1105, 42.7022), (76, "Iğdır", 39.9237, 44.0450),
    (77, "Yalova", 40.6500, 29.2667), (78, "Karabük", 41.2061, 32.6204),
    (79, "Kilis", 36.7184, 37.1212), (80, "Osmaniye", 37.0742, 36.2478),
    (81, "Düzce", 40.8438, 31.1565),
]

# Büyük şehirlerde merkezden daha geniş bir çember taranır (km).
_YARICAP = {
    34: 25, 6: 18, 35: 18, 7: 15, 16: 12, 1: 12, 42: 12, 27: 12, 33: 12, 41: 12,
    38: 10, 55: 10, 21: 10, 61: 10, 26: 10, 20: 10, 45: 10, 10: 10, 54: 10, 48: 12,
}

# Şehre gelmişken denenmesi gerekenler. Tıklanınca listede bu yemeği arar.
YORESEL_LEZZETLER = {
    1: ["Adana kebap", "Şalgam", "Bici bici"],
    2: ["Çiğ köfte"],
    3: ["Sucuk", "Kaymak", "Ekmek kadayıfı"],
    5: ["Keşkek", "Bakla dolması"],
    6: ["Ankara tava", "Beypazarı kurusu"],
    7: ["Tahinli piyaz", "Şiş köfte", "Hibeş"],
    9: ["Çöp şiş"],
    10: ["Höşmerim", "Susurluk tostu"],
    13: ["Büryan kebabı"],
    16: ["İskender", "İnegöl köfte", "Pideli köfte", "Kestane şekeri"],
    17: ["Peynir helvası"],
    19: ["Leblebi", "İskilip dolması"],
    20: ["Denizli kebabı"],
    21: ["Kaburga dolması", "Ciğer kebabı", "Meftune"],
    22: ["Tava ciğer", "Badem ezmesi"],
    23: ["Harput köftesi"],
    25: ["Cağ kebabı", "Kadayıf dolması"],
    26: ["Çibörek", "Met helvası", "Balaban kebabı"],
    27: ["Baklava", "Beyran", "Katmer", "Ali nazik", "Yuvalama"],
    31: ["Künefe", "Humus", "Oruk", "Tepsi kebabı"],
    33: ["Tantuni", "Cezerye", "Kerebiç"],
    34: ["Balık ekmek", "Midye dolma", "Kokoreç"],
    35: ["Boyoz", "Kumru", "İzmir köfte"],
    36: ["Kaz eti"],
    37: ["Banduma"],
    38: ["Mantı", "Pastırma", "Yağlama"],
    41: ["Pişmaniye"],
    42: ["Etli ekmek", "Fırın kebabı", "Tirit", "Bamya çorbası"],
    44: ["Kağıt kebabı", "Kayısı"],
    45: ["Manisa kebabı"],
    46: ["Maraş dondurması", "Eli böğründe"],
    47: ["Kaburga dolması", "Sembusek", "İçli köfte"],
    48: ["Çökertme kebabı"],
    50: ["Testi kebabı"],
    53: ["Kuymak", "Hamsi", "Laz böreği"],
    54: ["Islama köfte"],
    55: ["Bafra pidesi"],
    56: ["Büryan kebabı", "Perde pilavı"],
    58: ["Sivas köftesi"],
    59: ["Tekirdağ köftesi"],
    60: ["Tokat kebabı", "Bat"],
    61: ["Kuymak", "Akçaabat köftesi", "Hamsi", "Laz böreği"],
    63: ["Çiğ köfte", "Urfa kebabı", "Ciğer kebabı", "Şıllık"],
    65: ["Van kahvaltısı", "Otlu peynir"],
    79: ["Kilis tava"],
}


def _il_kaydi(plaka, ad, lat, lng):
    return {
        "plaka": plaka,
        "ad": ad,
        "slug": slugla(ad),
        "lat": lat,
        "lng": lng,
        "yaricap_km": _YARICAP.get(plaka, 8),
        "yoresel": YORESEL_LEZZETLER.get(plaka, []),
    }


ILLER = [_il_kaydi(*il) for il in _ILLER]
_PLAKA = {il["plaka"]: il for il in ILLER}
_ANAHTAR = {katla(il["ad"]): il for il in ILLER}
_ANAHTAR.update({il["slug"]: il for il in ILLER})
# Yaygın alternatif yazımlar
_ANAHTAR.update({"afyon": _PLAKA[3], "antakya": _PLAKA[31], "icel": _PLAKA[33],
                 "izmit": _PLAKA[41], "maras": _PLAKA[46], "urfa": _PLAKA[63],
                 "adapazari": _PLAKA[54], "antep": _PLAKA[27]})


def il_bul(deger) -> dict | None:
    """'34', 'istanbul', 'İSTANBUL', 'Urfa' gibi girdilerden il kaydını bulur."""
    if deger is None:
        return None
    metin = str(deger).strip()
    if not metin:
        return None
    if metin.isdigit():
        return _PLAKA.get(int(metin))
    return _ANAHTAR.get(katla(metin)) or _ANAHTAR.get(slugla(metin))
