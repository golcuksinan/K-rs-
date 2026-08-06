import hmac
from typing import Callable, Iterable, Optional

from limits import parse
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware, _should_exempt, sync_check_limits
from slowapi.wrappers import Limit
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match
from starlette.types import Scope

from app.core.config import settings
from app.core.security import decode_access_token


def from_cloudflare(request: Request) -> bool:
    secret = settings.CF_ORIGIN_SECRET
    if not secret:
        return False
    # Başlık latin-1 çözülür; str karşılaştırması ASCII dışı bir baytta TypeError atardı.
    sent = request.headers.get("x-origin-secret", "").encode("latin-1", "replace")
    return hmac.compare_digest(sent, secret.encode())


def client_ip(request: Request) -> str:
    """Cloudflare arkasında (Heroku) peer IP her zaman router'ın iç adresi olduğu için güven
    peer'a değil gizli başlığa bağlanır. Compose/nginx yolunda X-Forwarded-For yalnızca güvenilir
    ilan edilmiş bir proxy'den geliyorsa okunur; aksi halde başlık spoof edilerek limit tamamen
    atlatılabilirdi."""
    if from_cloudflare(request):
        cf_ip = request.headers.get("cf-connecting-ip", "").strip()
        if cf_ip:
            return cf_ip

    host = request.client.host if request.client else "127.0.0.1"
    if host in settings.trusted_proxy_ips_list:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return host


def rate_limit_key(request: Request) -> str:
    """Kimliği doğrulanmış istek kendi kovasını alır; NAT'ın arkasındaki kullanıcı artık
    kampüsle paylaşmaz. Token imzalı olduğu için forge edilemez, geçersizse sessizce IP'ye
    düşülür (401'i uç verir, limiter değil) ve anonim kova daha dar olduğu için token'ı
    düşürmek saldırgana bir şey kazandırmaz.

    `deps.py`'deki `password_changed_at` kontrolü bilinçli olarak tekrarlanmaz: her istekte
    bir DB sorgusu demek olurdu ve o token uçta zaten 401 alıyor.
    """
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        user_id, _ = decode_access_token(token.strip())
        if user_id is not None:
            return f"u:{user_id}"
    return client_ip(request)


limiter = Limiter(key_func=rate_limit_key, default_limits=[settings.RATE_LIMIT_DEFAULT])

# slowapi'nin sayacı isteği vurulduğu anda sayar, sonucu göremez; başarısızlık sayacı bu yüzden
# aynı depo üzerinde elle işletilir. İki eksen aynı `error_message`'ı paylaşır: 429 gövdesi
# hangi eksene takıldığını söylemesin.
_AUTH_FAILURE_MESSAGE = "Çok fazla başarısız giriş denemesi"


def _auth_failure_limit(limit_str: str, scope: str) -> Limit:
    return Limit(
        limit=parse(limit_str),
        key_func=client_ip,
        scope=scope,
        per_method=False,
        methods=None,
        error_message=_AUTH_FAILURE_MESSAGE,
        exempt_when=None,
        cost=1,
        override_defaults=False,
    )


AUTH_FAILURE_LIMIT = _auth_failure_limit(settings.RATE_LIMIT_AUTH_FAILURES, "auth-failures")
AUTH_FAILURE_EMAIL_LIMIT = _auth_failure_limit(
    settings.RATE_LIMIT_AUTH_FAILURES_EMAIL, "auth-failures-email"
)


def _auth_failure_axes(request: Request, email_hash: str) -> list[tuple]:
    return [
        (AUTH_FAILURE_LIMIT, ("auth-failures", client_ip(request))),
        (AUTH_FAILURE_EMAIL_LIMIT, ("auth-failures-email", email_hash)),
    ]


def auth_failures_exhausted(request: Request, email_hash: str) -> Optional[Limit]:
    """Tavanı dolmuş ekseni döner, yoksa None. Eksenler birbirinin yerine geçmez."""
    if not limiter.enabled:
        return None
    for limit, identifiers in _auth_failure_axes(request, email_hash):
        if not limiter.limiter.test(limit.limit, *identifiers):
            return limit
    return None


def record_auth_failure(request: Request, email_hash: str) -> None:
    if not limiter.enabled:
        return
    for limit, identifiers in _auth_failure_axes(request, email_hash):
        limiter.limiter.hit(limit.limit, *identifiers)


def _resolve_handler(route: BaseRoute, scope: Scope) -> Optional[Callable]:
    """FastAPI 0.139+ `include_router()` route'ları düz listeye açmıyor; eşleşen
    route bir `_IncludedRouter` ise `.endpoint`'i yok, içine inmek gerekiyor."""
    endpoint = getattr(route, "endpoint", None)
    if endpoint is not None:
        return endpoint

    match_fn = getattr(route, "_match", None)
    if match_fn is None:
        return None

    _match, _child_scope, matched, _ctx = match_fn(scope)
    if matched is None or matched is route:
        return None
    return _resolve_handler(matched, scope)


def _find_handler(routes: Iterable[BaseRoute], scope: Scope) -> Optional[Callable]:
    handler = None
    for route in routes:
        match, _ = route.matches(scope)
        if match != Match.FULL:
            continue
        resolved = _resolve_handler(route, scope)
        if resolved is not None:
            handler = resolved
    return handler


class NestedRouteSlowAPIMiddleware(SlowAPIMiddleware):
    """slowapi'nin kendi limit mantığını kullanır, sadece handler bulmayı düzeltir."""

    async def dispatch(self, request: Request, call_next) -> Response:
        app = request.app
        active_limiter: Limiter = app.state.limiter

        if not active_limiter.enabled:
            return await call_next(request)

        handler = _find_handler(app.routes, request.scope)
        if _should_exempt(active_limiter, handler):
            return await call_next(request)

        error_response, should_inject_headers = sync_check_limits(
            active_limiter, request, handler, app
        )
        if error_response is not None:
            return error_response

        response = await call_next(request)
        if should_inject_headers:
            response = active_limiter._inject_headers(
                response, request.state.view_rate_limit
            )
        return response
