import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.config import settings
from app.core.limiter import client_ip, from_cloudflare

SECRET = "gizli-deger"


@pytest.fixture
def locked(monkeypatch):
    monkeypatch.setattr(settings, "CF_ORIGIN_SECRET", SECRET)


def _request(headers: dict, host: str = "10.0.0.1") -> Request:
    raw = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (host, 1234)})


def test_kilit_kapaliyken_istek_gecer(client):
    assert client.get("/universities").status_code == 200


def test_dogru_gizli_deger_gecer(client, locked):
    resp = client.get("/universities", headers={"x-origin-secret": SECRET})
    assert resp.status_code == 200


def test_gizli_deger_yoksa_reddedilir(client, locked):
    resp = client.get("/universities")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Erişim reddedildi"


def test_yanlis_gizli_deger_reddedilir(client, locked):
    resp = client.get("/universities", headers={"x-origin-secret": SECRET + "x"})
    assert resp.status_code == 403


def test_ascii_disi_baslik_patlamaz(locked):
    # Ham 0xFF baytı latin-1 ile çözülür; str karşılaştırması burada TypeError atıp 500 verirdi.
    assert from_cloudflare(_request({"x-origin-secret": "\xff"})) is False


def test_health_kilitten_muaf(client, locked):
    assert client.get("/health").status_code == 200


def test_cf_connecting_ip_yalnizca_gizli_deger_dogruyken_okunur(locked):
    headers = {"x-origin-secret": SECRET, "cf-connecting-ip": "1.2.3.4"}
    assert client_ip(_request(headers)) == "1.2.3.4"

    headers["x-origin-secret"] = "yanlis"
    assert client_ip(_request(headers)) == "10.0.0.1"


def test_kilit_kapaliyken_cf_baslikligina_guvenilmez(monkeypatch):
    monkeypatch.setattr(settings, "CF_ORIGIN_SECRET", "")
    req = _request({"cf-connecting-ip": "1.2.3.4"})
    assert from_cloudflare(req) is False
    assert client_ip(req) == "10.0.0.1"
