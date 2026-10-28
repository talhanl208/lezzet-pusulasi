"""API anahtarı gerektirmeyen, kural tabanlı Türkçe yorum analizi.

Claude anahtarı yoksa (veya istek başarısız olursa) bu analiz kullanılır. Yorumları
cümleciklere böler, her cümlecikte hangi konudan (lezzet, servis...) bahsedildiğini ve
olumlu/olumsuz olduğunu sözlükle bulur, sonra kriter puanı ve artı/eksi listesi üretir.
"""
from __future__ import annotations

import re
import statistics

from .metin import katla
from .yemekler import yemekleri_bul

KONULAR = {
    "lezzet": ["lezzet", "tadi", "tadin", " tat ", "yemek", "nefis", "enfes", "pisir",
               "pismis", "sos", "baharat", "tuzlu", "yagli", "kuru ", "taze", "bayat",
               " et ", "etler", "kivam", "tatsiz", "damak"],
    "servis": ["garson", "servis", "personel", "calisan", "ilgi", "guler yuz", "kaba",
               "saygisiz", "nazik", "isletme sahibi", "sahibi", "kasiyer", "samimi",
               "karsilama", "kibar", "usta"],
    "fiyat_performans": ["fiyat", "pahali", "ucuz", "uygun", "hesap", "porsiyon", "doyurucu",
                         "kazik", "fahis", "deger", "f/p", "cebe", " para", "makul", " tl "],
    "temizlik": ["temiz", "kirli", "hijyen", "tuvalet", "lavabo", "sinek", "bocek", " pis ",
                 " kil ", "sac teli", "pislik", "bakimli"],
    "ambiyans": ["ortam", "atmosfer", "manzara", "dekor", "muzik", "gurultu", "kalabalik",
                 "ferah", "sikisik", "sirin", "salas", "keyifli", "oturma", "masa", "bahce",
                 "teras", "mekan"],
    "hiz": ["bekle", "hizli", "yavas", "gec geldi", "dakika", " sira ", "kuyruk", "cabuk",
            "uzun sure", "aninda", "cabucak", "geldi hemen"],
}
OLUMLU = ["harika", "mukemmel", "muhtesem", "enfes", "nefis", "lezzetli", "guzel", " iyi",
          "temiz", "hizli", "uygun", "ucuz", "ilgili", "guler yuz", "nazik", "keyifli", "ferah",
          "taze", "doyurucu", "tavsiye ederim", "basarili", "super", "efsane", "sahane",
          "bayildik", "begendik", "makul", "rahat", "samimi", "tertemiz", "bol ", "cabuk",
          "kaliteli", "yerinde", "degdi", "degerinde", "aninda", "kibar", "sirin", "bakimli",
          "memnun", "on numara", "10 numara", "tam kivam", "agizda dagil"]
OLUMSUZ = ["kotu", "berbat", "rezalet", "pahali", "kazik", "fahis", "kirli", " pis ", "yavas",
           "soguk geldi", "soguktu", "bayat", "lezzetsiz", "tatsiz", "kaba", "ilgisiz",
           "saygisiz", "bekledik", "beklettiler", "bekletildik", "gurultu", "sikisik", "yagli",
           "tuzlu", "kuru ", "az geldi", "porsiyon az", "porsiyonlar az", "kucuk porsiyon",
           "hayal kirikligi", "vasat", "idare eder", "sinek", "uzun sure", "gec geldi",
           "pisman", "tavsiye etmem", "bir daha gelmem", "kalitesiz", "ozensiz", " dar ",
           "suratsiz", "umursamaz", "fazla yazdi", "pislik", "bocek", " kil "]
_OLUMSUZLAMA = re.compile(r"\b(degil|degildi|degildir)\b")
_BOL = re.compile(r"[.!?;\n,]+|\s(?:ama|fakat|ancak|lakin|yalniz)\s")

TURIST_TUZAGI = ["kazik", "fahis", "turist", "hesap sis", "hesabi sis", "fiyat yazmiyor",
                 "fiyatsiz menu", "menude fiyat yok", "fazla yazdi", "fazla hesap", "kandir",
                 "dolandir"]

UYARI_KURALLARI = [
    (["kart gecmiyor", "kredi karti yok", "sadece nakit", "nakit calis"],
     "Kredi kartı geçmeyebilir, yanınızda nakit bulunsun"),
    (["rezervasyon sart", "yer bulamad", "rezervasyonsuz", "rezervasyon yapmadan"],
     "Yoğun saatlerde rezervasyon önerilir"),
    (["otopark yok", "park yeri yok", "park etmek zor", "park sorunu", "park yeri bulmak"],
     "Park yeri bulmak zor olabilir"),
    ([" sira ", "kuyruk"], "Yoğun saatlerde sıra olabiliyor"),
    (["kapaliydi", "acik yaziyor", "saatler yanlis"], "Gitmeden önce çalışma saatlerini teyit edin"),
]

KIMLERE = [
    (["aile", "cocuk"], "Aileler"),
    (["romantik", "sevgili", "esimle", "manzara", "ozel gun"], "Çiftler"),
    (["arkadas", "kalabalik grup", "grupla", "dogum gunu"], "Arkadaş grupları"),
    (["ogle yemeg", "ogle arasi", "is cikisi", "ayakustu"], "Hızlı öğle yemeği"),
    (["gece", "gec saat", "sabaha kadar"], "Gece acıkanlar"),
]

ARTI_CUMLELERI = {
    "lezzet": ("Yemeklerin lezzeti çok beğeniliyor", "Lezzet genel olarak iyi bulunuyor"),
    "servis": ("Personel güler yüzlü ve ilgili", "Servis genel olarak memnun ediyor"),
    "fiyat_performans": ("Fiyat/performansı güçlü, porsiyonlar doyurucu",
                         "Fiyatlar aldığınıza göre makul"),
    "temizlik": ("Mekan temiz ve bakımlı", "Temizlik konusunda olumlu yorumlar var"),
    "ambiyans": ("Ortamı keyifli ve rahat", "Ortam genel olarak beğeniliyor"),
    "hiz": ("Siparişler hızlı geliyor", "Servis hızı yeterli bulunuyor"),
}
EKSI_CUMLELERI = {
    "lezzet": ("Yemeklerin lezzeti sık sık eleştiriliyor",
               "Lezzetin tutarsız ya da vasat olduğu yorumları var"),
    "servis": ("Personelin ilgisizliği/kabalığı çok şikayet ediliyor",
               "Servis zaman zaman eleştiriliyor"),
    "fiyat_performans": ("Fiyatlar porsiyonlara göre yüksek bulunuyor",
                         "Bazı yorumlarda fiyatlar pahalı bulunuyor"),
    "temizlik": ("Temizlik/hijyen şikayetleri dikkat çekiyor",
                 "Temizlikle ilgili olumsuz yorumlar var"),
    "ambiyans": ("Ortam kalabalık/gürültülü bulunuyor", "Ortam bazı ziyaretçilere sıkışık geliyor"),
    "hiz": ("Bekleme süreleri uzun", "Yoğun saatlerde servis yavaşlayabiliyor"),
}
KRITER_ADI = {"lezzet": "lezzeti", "servis": "servisi", "fiyat_performans": "fiyat/performansı",
              "temizlik": "temizliği", "ambiyans": "ortamı", "hiz": "hızı"}

_KISI_BASI = re.compile(r"kisi bas[iı]\D{0,15}(\d{2,5})\s*(?:tl|₺|lira)|(\d{2,5})\s*(?:tl|₺|lira)\D{0,15}kisi bas")


def _say(metin: str, kelimeler) -> int:
    return sum(metin.count(k) for k in kelimeler)


def _hazirla(metin: str) -> str:
    k = f" {katla(metin)} "
    # Yemek adları sözlükle çakışmasın
    return k.replace("kuru fasulye", "kurufasulye")


def analiz_et(mekan: dict, yorumlar: list[dict]) -> dict:
    sayac = {k: {"pos": 0.0, "neg": 0.0, "yildiz": []} for k in KONULAR}
    yemek_sayac: dict[str, float] = {}
    tum_metin = []
    yildizlar = []

    kaynaklar = [(y.get("metin") or "", y.get("puan")) for y in yorumlar]
    if mekan.get("google_ozet"):
        kaynaklar.append((mekan["google_ozet"], None))

    for metin, yildiz in kaynaklar:
        if not metin.strip():
            if yildiz:
                yildizlar.append(yildiz)
            continue
        if yildiz:
            yildizlar.append(yildiz)
        hazir = _hazirla(metin)
        tum_metin.append(hazir)
        for parca in _BOL.split(hazir):
            parca = f" {parca.strip()} "
            if len(parca.strip()) < 3:
                continue
            pos, neg = _say(parca, OLUMLU), _say(parca, OLUMSUZ)
            if _OLUMSUZLAMA.search(parca):
                pos, neg = neg, pos
            if pos == neg == 0 and yildiz:
                pos, neg = (0.5, 0) if yildiz >= 4 else (0, 0.5) if yildiz <= 2 else (0, 0)
            for konu, kelimeler in KONULAR.items():
                if any(k in parca for k in kelimeler):
                    sayac[konu]["pos"] += min(pos, 2)
                    sayac[konu]["neg"] += min(neg, 2)
                    if yildiz:
                        sayac[konu]["yildiz"].append(yildiz)
            if pos > neg or (pos == neg == 0 and (yildiz or 0) >= 4):
                for yemek in yemekleri_bul(parca):
                    yemek_sayac[yemek] = yemek_sayac.get(yemek, 0) + 1

    kriterler = {}
    for konu, s in sayac.items():
        if s["pos"] + s["neg"] < 1:
            kriterler[konu] = None
            continue
        # Laplace düzeltmeli oran; az kanıtla uç puan (1 ya da 10) çıkmasın
        sozluk_puani = 1.5 + 8 * (s["pos"] + 1) / (s["pos"] + s["neg"] + 2)
        if s["yildiz"]:
            yildiz_puani = 1 + (statistics.mean(s["yildiz"]) - 1) * 2.25
            puan = 0.65 * sozluk_puani + 0.35 * yildiz_puani
        else:
            puan = sozluk_puani
        kriterler[konu] = int(round(max(1, min(10, puan))))

    butun = " ".join(tum_metin)
    one_cikan = [y for y, _ in sorted(yemek_sayac.items(), key=lambda x: -x[1])][:5]

    artilar = []
    for konu, puan in sorted(((k, p) for k, p in kriterler.items() if p and p >= 7),
                             key=lambda x: -x[1]):
        guclu, normal = ARTI_CUMLELERI[konu]
        artilar.append(guclu if puan >= 8 else normal)
    if one_cikan:
        artilar.insert(0 if len(artilar) < 2 else 1,
                       f"{', '.join(one_cikan[:3])} özellikle övülüyor")
    eksiler = []
    for konu, puan in sorted(((k, p) for k, p in kriterler.items() if p and p <= 5),
                             key=lambda x: x[1]):
        cok, biraz = EKSI_CUMLELERI[konu]
        eksiler.append(cok if puan <= 3 else biraz)

    turist = _say(butun, TURIST_TUZAGI)
    fp = kriterler.get("fiyat_performans")
    turist_riski = turist >= 2 or (turist >= 1 and fp is not None and fp <= 4)
    if turist_riski:
        eksiler.insert(0, "Fahiş fiyat / hesapta sürpriz şikayetleri var")

    uyarilar = [mesaj for kaliplar, mesaj in UYARI_KURALLARI if any(k in butun for k in kaliplar)]
    kimlere = [ad for kaliplar, ad in KIMLERE if any(k in butun for k in kaliplar)]
    oz = mekan.get("ozellikler") or {}
    if oz.get("cocuk") and "Aileler" not in kimlere:
        kimlere.append("Aileler")
    if oz.get("grup") and "Arkadaş grupları" not in kimlere:
        kimlere.append("Arkadaş grupları")

    fiyatlar = [int(a or b) for a, b in _KISI_BASI.findall(butun) if (a or b)]
    kisi_basi = int(statistics.median(fiyatlar)) if fiyatlar else None

    return {
        "yontem": "kural",
        "ozet": _ozet_yaz(kriterler, yildizlar, one_cikan),
        "artilar": artilar[:5],
        "eksiler": eksiler[:5],
        "kriterler": kriterler,
        "one_cikan_lezzetler": one_cikan,
        "uyarilar": uyarilar[:3],
        "turist_tuzagi_riski": turist_riski,
        "kimlere_uygun": kimlere[:4],
        "kisi_basi_tahmin_tl": kisi_basi,
        "yorum_adedi": len(yorumlar),
    }


def _ozet_yaz(kriterler: dict, yildizlar: list, one_cikan: list) -> str:
    if not yildizlar and not any(kriterler.values()):
        return "Analiz için yeterli yorum yok."
    ort = statistics.mean(yildizlar) if yildizlar else None
    if ort is None:
        genel = "Yorumlardan sınırlı bilgi çıkıyor"
    elif ort >= 4.3:
        genel = "Yorumların büyük çoğunluğu olumlu"
    elif ort >= 3.4:
        genel = "Yorumlar karışık ama olumlu tarafı ağır basıyor"
    elif ort >= 2.6:
        genel = "Yorumlar oldukça karışık"
    else:
        genel = "Olumsuz yorumlar ağır basıyor"
    iyiler = [KRITER_ADI[k] for k, p in sorted(kriterler.items(), key=lambda x: -(x[1] or 0))
              if p and p >= 7][:2]
    cumle = genel + "."
    if iyiler:
        cumle += f" En çok {' ve '.join(iyiler)} öne çıkıyor."
    if one_cikan:
        cumle += f" Önerilenler: {', '.join(one_cikan[:3]).lower()}."
    return cumle
