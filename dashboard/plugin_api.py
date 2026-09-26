"""SuperGrok weekly pool for the desktop status-bar chip.

Uses the same billing backend Grok CLI uses. Not a public xAI API.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter

BILLING_URL = "https://cli-chat-proxy.grok.com/v1/billing?format=credits"
# ponytail: 90s process cache; drop if xAI rate-limits this host.
_TTL = 90.0
# (fetched_at, token_fingerprint, payload)
_cache: tuple[float, str, dict[str, Any]] | None = None

router = APIRouter()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def parse_credits(payload: dict[str, Any]) -> dict[str, Any]:
    cfg = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    pct = _finite_number(cfg.get("creditUsagePercent"))
    period = cfg.get("currentPeriod") if isinstance(cfg.get("currentPeriod"), dict) else {}
    ptype = str(period.get("type") or "")
    if "WEEKLY" in ptype:
        kind = "weekly"
    elif "MONTHLY" in ptype:
        kind = "monthly"
    else:
        kind = "unknown"
    products: list[dict[str, Any]] = []
    raw_products = cfg.get("productUsage")
    if isinstance(raw_products, list):
        for item in raw_products:
            if not isinstance(item, dict):
                continue
            item_pct = _finite_number(item.get("usagePercent"))
            if item_pct is None:
                continue
            products.append({"product": item.get("product"), "pct": item_pct})
    if pct is None:
        return {"ok": False, "error": "no_percent"}
    return {
        "ok": True,
        "used_percent": pct,
        "left_percent": 100.0 - pct,
        "period": kind,
        "resets_at": period.get("end"),
        "starts_at": period.get("start"),
        "products": products,
    }


def _token() -> str:
    from hermes_cli.auth import resolve_xai_oauth_runtime_credentials

    creds = resolve_xai_oauth_runtime_credentials()
    return str(creds.get("api_key") or creds.get("access_token") or "").strip()


def _token_fp(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def _classify_auth_error(exc: BaseException) -> str:
    if isinstance(exc, (ImportError, ModuleNotFoundError, KeyError, ValueError)):
        return "no_auth"
    text = str(exc).lower()
    terminal = (
        "invalid_grant",
        "revoked",
        "login",
        "no token",
        "not authenticated",
        "unauthorized",
        "quarantine",
    )
    if any(marker in text for marker in terminal):
        return "no_auth"
    return "auth_refresh_failed"


def fetch_usage() -> dict[str, Any]:
    global _cache
    now = time.time()
    try:
        token = _token()
    except Exception as exc:
        _cache = None
        return {"ok": False, "error": _classify_auth_error(exc)}
    if not token:
        _cache = None
        return {"ok": False, "error": "no_auth"}
    fp = _token_fp(token)
    if _cache and now - _cache[0] < _TTL and _cache[1] == fp:
        return _cache[2]
    req = urllib.request.Request(
        BILLING_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            _cache = None
            return {"ok": False, "error": "no_auth"}
        return {"ok": False, "error": f"http_{exc.code}"}
    except Exception:
        return {"ok": False, "error": "fetch_failed"}
    if not isinstance(raw, dict):
        return {"ok": False, "error": "bad_json"}
    out = parse_credits(raw)
    if out.get("ok"):
        _cache = (now, fp, out)
    return out


def snapshot_to_usage(snap: Any) -> dict[str, Any]:
    """Core AccountUsageSnapshot -> chip payload; the busiest window drives the label."""
    if snap is None:
        return {"ok": False, "error": "no_auth"}
    if getattr(snap, "unavailable_reason", None):
        return {"ok": False, "error": "no_oauth"}
    windows = []
    for w in snap.windows:
        pct = _finite_number(w.used_percent)
        if pct is None:
            continue
        reset = w.reset_at.isoformat() if w.reset_at else None
        windows.append({"label": w.label, "used_percent": pct, "resets_at": reset})
    if not windows:
        return {"ok": False, "error": "no_percent"}
    top = max(windows, key=lambda w: w["used_percent"])
    return {
        "ok": True,
        "used_percent": top["used_percent"],
        "left_percent": 100.0 - top["used_percent"],
        "period": top["label"],
        "resets_at": top["resets_at"],
        "plan": snap.plan,
        "windows": windows,
    }


# ponytail: 90s cache per provider, same as Grok.
_core_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_CORE_PROVIDERS = {"chatgpt": "openai-codex", "claude": "anthropic"}


def fetch_core_usage(kind: str) -> dict[str, Any]:
    now = time.time()
    hit = _core_cache.get(kind)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    from agent.account_usage import fetch_account_usage

    out = snapshot_to_usage(fetch_account_usage(_CORE_PROVIDERS[kind]))
    if out.get("ok"):
        _core_cache[kind] = (now, out)
    return out


@router.get("/usage")
def usage(provider: str = "grok") -> dict[str, Any]:
    if provider in _CORE_PROVIDERS:
        return fetch_core_usage(provider)
    return fetch_usage()


if __name__ == "__main__":
    sample = {
        "config": {
            "creditUsagePercent": 42.5,
            "currentPeriod": {
                "type": "USAGE_PERIOD_TYPE_WEEKLY",
                "start": "2026-06-01T00:00:00Z",
                "end": "2026-06-08T00:00:00Z",
            },
            "productUsage": [{"product": "GrokBuild", "usagePercent": 42.5}],
        }
    }
    parsed = parse_credits(sample)
    assert parsed["ok"] and parsed["used_percent"] == 42.5
    assert parsed["left_percent"] == 57.5
    assert parsed["period"] == "weekly"
    assert parse_credits({"config": {"creditUsagePercent": True}})["error"] == "no_percent"
    assert parse_credits({"config": {"creditUsagePercent": float("nan")}})["error"] == "no_percent"
    weird = parse_credits({"config": {"creditUsagePercent": 10, "productUsage": 1}})
    assert weird["ok"] and weird["products"] == []
    json.dumps(weird)
    json.dumps(parse_credits({"config": {"creditUsagePercent": float("nan")}}))

    from datetime import datetime, timezone
    from types import SimpleNamespace as NS

    snap = NS(unavailable_reason=None, plan="Team", windows=[
        NS(label="Session", used_percent=19.0, reset_at=datetime(2026, 9, 26, tzinfo=timezone.utc)),
        NS(label="Weekly", used_percent=3.0, reset_at=None),
        NS(label="Broken", used_percent=float("nan"), reset_at=None),
    ])
    core = snapshot_to_usage(snap)
    assert core["ok"] and core["period"] == "Session" and core["left_percent"] == 81.0
    assert len(core["windows"]) == 2
    json.dumps(core)
    assert snapshot_to_usage(None)["error"] == "no_auth"
    assert snapshot_to_usage(NS(unavailable_reason="api key", windows=[]))["error"] == "no_oauth"

    saved_token = _token
    saved_cache = _cache
    try:
        def _boom() -> str:
            raise RuntimeError("refresh timeout")

        globals()["_token"] = _boom
        globals()["_cache"] = (time.time(), "stale", {"ok": True, "used_percent": 9})
        failed = fetch_usage()
        assert failed == {"ok": False, "error": "auth_refresh_failed"}
        assert globals()["_cache"] is None

        globals()["_token"] = lambda: ""
        globals()["_cache"] = (time.time(), "stale", {"ok": True, "used_percent": 9})
        missing = fetch_usage()
        assert missing == {"ok": False, "error": "no_auth"}
        assert globals()["_cache"] is None
    finally:
        globals()["_token"] = saved_token
        globals()["_cache"] = saved_cache

    for name in ("grok", "chatgpt", "claude"):
        live = usage(name)
        if live.get("ok"):
            print(f"{name} {live['left_percent']:.0f}% left {live['period']} reset {live.get('resets_at')}")
        else:
            print(name, "unavailable", live.get("error"))
