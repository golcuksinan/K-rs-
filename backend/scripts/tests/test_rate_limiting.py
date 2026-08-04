"""Cross-cutting: main.py'deki slowapi rate limiting middleware'i (varsayılan 20/saniye + 100/dakika).

Diğer tüm testlerde rate limiting `_disable_rate_limiting` (autouse) ile kapalıdır;
bu dosyadaki testler `enable_rate_limiting` fixture'ını isteyip özel olarak açar.
"""

import ast
import os
import pathlib
import subprocess
import sys
import time

from app.core.config import settings
from app.core.security import create_access_token


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
        """Auth uçlarında dakikalık kova global olandan dar.

        slowapi uç bazlı limitin *üstüne* varsayılanları da ekliyor, dolayısıyla 429'un
        auth kovasından geldiğini göstermek için istekler saniyelik pencereye sığmayacak
        şekilde ikiye bölünüp aralarında pencere sıfırlanıyor.

        Uç olarak login değil forgot-password seçildi: login'de başarısızlık sayacı (§3.4)
        daha dar ve önce dolar, ölçülen şey istek limiti olmaktan çıkardı.
        """
        allowed = int(settings.RATE_LIMIT_AUTH.split("/")[0])
        payload = {"email": "yok@posta.pau.edu.tr"}
        half = allowed // 2 + 1

        statuses = [
            client.post("/auth/forgot-password", json=payload).status_code
            for _ in range(half)
        ]
        time.sleep(1.05)
        statuses += [
            client.post("/auth/forgot-password", json=payload).status_code
            for _ in range(allowed + 1 - half)
        ]

        assert statuses == [200] * allowed + [429]


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


class TestAuthFailureCounter:
    """§3.4: auth uçlarında istek değil başarısızlık sayılır, iki eksende birden.

    IP ekseni spraying'i (çok hesap, tek kaynak), e-posta ekseni tek hesabı hedefleyeni
    yakalar. Eksenleri ayırt edebilmek için IP eksenini ölçen testler her istekte farklı
    e-posta kullanır, yoksa dar olan e-posta ekseni önce dolar.
    """

    @property
    def ip_allowed(self) -> int:
        return int(settings.RATE_LIMIT_AUTH_FAILURES.split("/")[0])

    @property
    def email_allowed(self) -> int:
        return int(settings.RATE_LIMIT_AUTH_FAILURES_EMAIL.split("/")[0])

    def _fail(self, client, email="yok@posta.pau.edu.tr"):
        return client.post(
            "/auth/login", json={"email": email, "password": "YanlisSifre1"}
        )

    def _fail_distinct(self, client, i):
        return self._fail(client, f"yok{i}@posta.pau.edu.tr")

    def test_ip_ekseni_tavanda_429_ve_slowapi_govdesi(self, client, enable_rate_limiting):
        statuses = [
            self._fail_distinct(client, i).status_code for i in range(self.ip_allowed)
        ]
        assert statuses == [401] * self.ip_allowed

        blocked = self._fail_distinct(client, self.ip_allowed)
        assert blocked.status_code == 429
        # Sözleşme: 429 gövdesi "detail" değil "error" (bkz. api-contract.md §hata gövdeleri).
        assert "error" in blocked.json()

    def test_eposta_ekseni_ip_tavanindan_once_dolar(self, client, enable_rate_limiting):
        statuses = [self._fail(client).status_code for _ in range(self.email_allowed)]
        assert statuses == [401] * self.email_allowed
        assert self._fail(client).status_code == 429

    def test_eposta_ekseni_diger_adresleri_kilitlemez(self, client, enable_rate_limiting):
        """Tek hesabı hedefleyen saldırı, aynı IP'deki başka kullanıcıyı kilitlemez."""
        for _ in range(self.email_allowed + 1):
            self._fail(client)

        assert self._fail(client, "baska@posta.pau.edu.tr").status_code == 401

    def test_basarili_giris_sayaci_tuketmez(self, client, enable_rate_limiting, student):
        payload = {"email": student["email"], "password": student["password"]}
        for _ in range(5):
            assert client.post("/auth/login", json=payload).status_code == 200

        statuses = [
            self._fail_distinct(client, i).status_code for i in range(self.ip_allowed)
        ]
        assert statuses == [401] * self.ip_allowed

    def test_tavan_dolunca_dogru_sifre_de_reddedilir(
        self, client, enable_rate_limiting, student
    ):
        """Kontrol şifre doğrulamasından önce; saldırgana bcrypt maliyeti de ödetilmiyor."""
        for i in range(self.ip_allowed):
            self._fail_distinct(client, i)

        resp = client.post(
            "/auth/login",
            json={"email": student["email"], "password": student["password"]},
        )
        assert resp.status_code == 429


class TestUserKeyedLimits:
    """§3.4: geçerli token varsa kova IP değil kullanıcı başına.

    Token limiter'da DB'ye bakılmadan çözüldüğü için testlerde gerçek kullanıcı gerekmiyor.
    """

    def _headers(self, user_id: int) -> dict:
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def _drain(self, client, headers=None):
        for _ in range(105):
            if client.get("/universities", headers=headers).status_code == 429:
                return
        raise AssertionError("limit tetiklenmedi")

    def test_iki_kullanici_ayri_kovalarda(self, client, enable_rate_limiting):
        self._drain(client, self._headers(1))

        assert client.get("/universities", headers=self._headers(2)).status_code == 200

    def test_token_kullaniciyi_ip_kovasindan_cikarir(self, client, enable_rate_limiting):
        self._drain(client)

        assert client.get("/universities", headers=self._headers(1)).status_code == 200

    def test_gecersiz_token_ip_kovasina_duser(self, client, enable_rate_limiting):
        """Çöp token göndererek kovayı sıfırlamak işe yaramamalı."""
        self._drain(client)

        headers = {"Authorization": "Bearer cop-token"}
        assert client.get("/universities", headers=headers).status_code == 429

    def test_auth_uclari_token_a_ragmen_ip_ekseninde_kalir(self, client, enable_rate_limiting):
        allowed = int(settings.RATE_LIMIT_AUTH.split("/")[0])
        payload = {"email": "yok@posta.pau.edu.tr"}
        half = allowed // 2 + 1

        # İkiye bölünüyor ki tavana çarpan şey saniyelik varsayılan değil, IP'ye bağlı
        # dakikalık auth limiti olsun.
        for _ in range(half):
            client.post("/auth/forgot-password", json=payload, headers=self._headers(1))
        time.sleep(1.05)
        for _ in range(allowed - half):
            client.post("/auth/forgot-password", json=payload, headers=self._headers(1))

        blocked = client.post(
            "/auth/forgot-password", json=payload, headers=self._headers(2)
        )
        assert blocked.status_code == 429


class TestLimitsFromEnv:
    """Limitler import anında okunuyor, monkeypatch geç kalır — ayrı süreçte doğrulanır."""

    def _read_limits(self, **env):
        script = (
            "from app.core.limiter import limiter\n"
            "from app.api import auth\n"
            "print([str(x.limit) for x in limiter._default_limits[0]])\n"
            "print([str(x.limit) for x in limiter._route_limits['app.api.auth.login']])\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=pathlib.Path(__file__).resolve().parents[2],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        default, authed = result.stdout.strip().splitlines()[-2:]
        return ast.literal_eval(default), ast.literal_eval(authed)

    def test_env_degerleri_limiter_a_ulasir(self):
        default, authed = self._read_limits(
            RATE_LIMIT_DEFAULT="7/minute", RATE_LIMIT_AUTH="3/hour"
        )
        assert default == ["7 per 1 minute"]
        assert authed == ["3 per 1 hour"]

    def test_noktali_virgul_birden_cok_pencere_verir(self):
        # .env'de ";" yorum başlatmıyor; bozulursa limit tek pencereye düşerdi.
        default, _ = self._read_limits(RATE_LIMIT_DEFAULT="2/second;9/minute")
        assert default == ["2 per 1 second", "9 per 1 minute"]

    def test_varsayilanlar_kod_ve_env_ornegiyle_ayni(self):
        default, authed = self._read_limits()
        assert default == ["20 per 1 second", "600 per 1 minute"]
        assert authed == ["20 per 1 minute"]