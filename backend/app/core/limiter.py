from typing import Callable, Iterable, Optional

from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware, _should_exempt, sync_check_limits
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match
from starlette.types import Scope

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


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
