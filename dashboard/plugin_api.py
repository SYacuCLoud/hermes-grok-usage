"""SuperGrok weekly pool for the desktop status-bar chip.

Uses the same billing backend Grok CLI uses. Not a public xAI API.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter

BILLING_URL = "https://cli-chat-proxy.grok.com/v1/billing?format=credits"
# ponytail: 90s process cache; drop if xAI rate-limits this host.
_TTL = 90.0
_cache: tuple[float, dict[str, Any]] | None = None

router = APIRouter()


def parse_credits(payload: dict[str, Any]) -> dict[str, Any]:
    cfg = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    pct = cfg.get("creditUsagePercent")
    period = cfg.get("currentPeriod") if isinstance(cfg.get("currentPeriod"), dict) else {}
    ptype = str(period.get("type") or "")
    if "WEEKLY" in ptype:
        kind = "weekly"
    elif "MONTHLY" in ptype:
        kind = "monthly"
    else:
        kind = "unknown"
    products = []
    for item in cfg.get("productUsage") or []:
        if isinstance(item, dict) and isinstance(item.get("usagePercent"), (int, float)):
            products.append({"product": item.get("product"), "pct": item["usagePercent"]})
    if not isinstance(pct, (int, float)):
        return {"ok": False, "error": "no_percent"}
    return {
        "ok": True,
        "used_percent": float(pct),
        "period": kind,
        "resets_at": period.get("end"),
        "starts_at": period.get("start"),
        "products": products,
    }


def _token() -> str:
    from hermes_cli.auth import resolve_xai_oauth_runtime_credentials

    creds = resolve_xai_oauth_runtime_credentials()
    return str(creds.get("api_key") or creds.get("access_token") or "").strip()


def fetch_usage() -> dict[str, Any]:
    global _cache
    now = time.time()
    if _cache and now - _cache[0] < _TTL:
        return _cache[1]
    token = _token()
    if not token:
        return {"ok": False, "error": "no_auth"}
    req = urllib.request.Request(
        BILLING_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"http_{exc.code}"}
    except Exception:
        return {"ok": False, "error": "fetch_failed"}
    if not isinstance(raw, dict):
        return {"ok": False, "error": "bad_json"}
    out = parse_credits(raw)
    if out.get("ok"):
        _cache = (now, out)
    return out


@router.get("/usage")
def usage() -> dict[str, Any]:
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
    assert parsed["period"] == "weekly"
    live = fetch_usage()
    if live.get("ok"):
        print(f"Grok {live['used_percent']:.0f}% {live['period']} reset {live.get('resets_at')}")
    else:
        print("unavailable", live.get("error"))
