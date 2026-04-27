"""Legacy URL → V2 301 redirect middleware.

Mirrors the table declared in ``dashboard/src/app/v2/redirects.ts`` so that
crawlers, bookmarks, curl and social-unfurlers hit the V2 URL without needing
client-side JavaScript.

Lot 6 — Bloc A (migration cutover).

Semantics
---------
* Static entries : exact path match → ``RedirectResponse(status_code=301)``.
* Dynamic entries : ``/football/match/{id}`` propagates ``{id}`` as-is to the
  target suffix (``/matchs/{id}``).
* Query params : incoming query wins on key collisions. Target-side injected
  params (e.g. ``?sport=foot``) are added only when absent from incoming.
* ``preserveQuery=False`` (only ``/hero-showcase``) drops the incoming query.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp

# ─── Redirect table (source of truth mirror) ──────────────────────────

#: Static exact-match redirects.
#:
#: Format : source_path → (target_path, injected_query_params, preserve_query)
_STATIC_REDIRECTS: dict[str, tuple[str, dict[str, str], bool]] = {
    "/paris-du-soir": ("/matchs", {"signal": "value"}, True),
    "/paris-du-soir/football": (
        "/matchs",
        {"sport": "foot", "signal": "value"},
        True,
    ),
    "/football": ("/matchs", {"sport": "foot"}, True),
    "/nhl": ("/matchs", {"sport": "nhl"}, True),
    "/watchlist": ("/compte/bankroll", {}, True),
    "/hero-showcase": ("/", {}, False),
}

#: Dynamic prefix redirects : ``/{prefix}/{suffix}`` → ``/{target_prefix}/{suffix}``.
_DYNAMIC_REDIRECTS: list[tuple[str, str]] = [
    ("/football/match/", "/matchs/"),
    ("/nhl/match/", "/matchs/"),
]


def _build_location(
    target: str,
    incoming_qs: str,
    inject: dict[str, str],
    preserve_query: bool,
) -> str:
    """Merge target + incoming query strings per the documented semantics."""
    if not preserve_query:
        # Drop incoming entirely; keep only injected params on target.
        if not inject:
            return target
        return f"{target}?{urlencode(inject)}"

    # preserveQuery=True : incoming wins, target injects only if key missing.
    merged: dict[str, str] = dict(parse_qsl(incoming_qs, keep_blank_values=True))
    for key, value in inject.items():
        merged.setdefault(key, value)

    return f"{target}?{urlencode(merged)}" if merged else target


class LegacyRedirectMiddleware(BaseHTTPMiddleware):
    """Intercepts legacy paths and emits ``301`` with the V2 Location."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path
        incoming_qs = request.url.query

        # Static match
        static_entry = _STATIC_REDIRECTS.get(path)
        if static_entry is not None:
            target, inject, preserve = static_entry
            location = _build_location(target, incoming_qs, inject, preserve)
            return RedirectResponse(url=location, status_code=301)

        # Dynamic prefix match
        for prefix, target_prefix in _DYNAMIC_REDIRECTS:
            if path.startswith(prefix):
                suffix = path[len(prefix) :]
                # Only treat as dynamic when there IS a suffix (no empty path).
                # That protects against `/football/match/` with trailing slash.
                if suffix:
                    target = f"{target_prefix}{suffix}"
                    location = _build_location(target, incoming_qs, {}, True)
                    return RedirectResponse(url=location, status_code=301)

        return await call_next(request)
