"""Cross-cutting: main.py'deki slowapi rate limiting middleware'i (varsayılan 20/saniye + 100/dakika).

Diğer tüm testlerde rate limiting `_disable_rate_limiting` (autouse) ile kapalıdır;
bu dosyadaki testler `enable_rate_limiting` fixture'ını isteyip özel olarak açar.
"""


class TestRateLimiting:
    def test_health_check_is_exempt_from_rate_limit(self, client, enable_rate_limiting):
        for _ in range(105):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_default_limit_returns_429_after_threshold(self, client, enable_rate_limiting):
        statuses = []
        for _ in range(105):
            resp = client.get("/universities")
            statuses.append(resp.status_code)
            if resp.status_code == 429:
                break

        assert 429 in statuses

    def test_auth_endpoints_have_stricter_limit(self, client, enable_rate_limiting):
        """Auth uçlarında global limit değil, uç bazlı 5/dakika geçerli.

        İlk beşin 401 dönmesi bir sözleşme: auth uçlarına saniyelik pencere eklenirse
        (5'ten dar bir değerle) burası kırılır — kasıtlı.
        """
        payload = {"email": "yok@posta.pau.edu.tr", "password": "YanlisSifre1"}
        statuses = [client.post("/auth/login", json=payload).status_code for _ in range(6)]

        assert statuses[:5] == [401] * 5
        assert statuses[5] == 429


def _drain_until_429(client, forwarded_for):
    for _ in range(105):
        resp = client.get("/universities", headers={"X-Forwarded-For": forwarded_for})
        if resp.status_code == 429:
            return
    raise AssertionError("limit tetiklenmedi")


class TestForwardedForKey:
    def test_forwarded_for_ignored_without_trusted_proxy(self, client, enable_rate_limiting):
        # Eşitlik üzerinden iddia ediliyor: pencere tam araya denk gelirse ikisi de 200 olur,
        # ayrı kovalara düşen bozuk bir uygulamada ise ikisi ayrışır.
        _drain_until_429(client, "1.1.1.1")

        other = client.get("/universities", headers={"X-Forwarded-For": "2.2.2.2"})
        same = client.get("/universities", headers={"X-Forwarded-For": "1.1.1.1"})

        assert other.status_code == same.status_code

    def test_forwarded_for_splits_buckets_behind_trusted_proxy(
        self, client, enable_rate_limiting, monkeypatch
    ):
        from app.core.config import settings

        # TestClient'ta request.client.host "testclient" stringidir.
        monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "testclient")
        _drain_until_429(client, "1.1.1.1")

        other = client.get("/universities", headers={"X-Forwarded-For": "2.2.2.2"})

        assert other.status_code == 200