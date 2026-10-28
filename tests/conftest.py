import json
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from pusula import create_app  # noqa: E402


def veri(ad):
    with open(os.path.join(KOK, "tests", "veri", ad), encoding="utf-8") as f:
        return json.load(f)


class SahteYanit:
    def __init__(self, govde, durum=200, basliklar=None):
        self._govde = govde
        self.status_code = durum
        self.headers = basliklar or {}
        self.text = json.dumps(govde, ensure_ascii=False)

    def json(self):
        return self._govde


class SahteOturum:
    """requests.Session yerine geçer; istekleri kaydeder, sıradaki yanıtı döndürür."""

    def __init__(self, yanitlar):
        self.yanitlar = list(yanitlar)
        self.istekler = []

    def _yanit(self, **kayit):
        self.istekler.append(kayit)
        y = self.yanitlar.pop(0) if len(self.yanitlar) > 1 else self.yanitlar[0]
        return y if isinstance(y, SahteYanit) else SahteYanit(y)

    def request(self, yontem, url, **kw):
        return self._yanit(yontem=yontem, url=url, **kw)

    def post(self, url, **kw):
        return self._yanit(yontem="POST", url=url, **kw)

    def get(self, url, **kw):
        return self._yanit(yontem="GET", url=url, **kw)


@pytest.fixture
def uygulama(tmp_path):
    app = create_app({"VERITABANI": str(tmp_path / "test.sqlite3"), "DEMO": True,
                      "ISLER_SENKRON": True, "TESTING": True, "SECRET_KEY": "test",
                      "GOOGLE_PLACES_API_KEY": "", "ANTHROPIC_API_KEY": "", "SERPAPI_API_KEY": "",
                      "GOOGLE_MAPS_JS_KEY": ""})
    return app


@pytest.fixture
def istemci(uygulama):
    return uygulama.test_client()
