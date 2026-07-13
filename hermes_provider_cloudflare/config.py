"""Cloudflare Workers AI configuration helpers."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlparse

_DIRECT_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
_CATALOG_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search"
_GATEWAY_BASE_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/v1"


def normalize_inference_base_url(value: str) -> str:
    """Return a normalized credential-safe inference URL or an empty string."""
    normalized = str(value or "").strip().rstrip("/")
    if not normalized:
        return ""
    try:
        parsed = urlparse(normalized)
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port == 0
        or parsed.query
        or parsed.fragment
    ):
        return ""
    return normalized


def build_inference_base_url(env: Mapping[str, str]) -> str:
    """Build a concrete Workers AI OpenAI-compatible inference URL."""
    override = normalize_inference_base_url(env.get("CLOUDFLARE_WORKERS_AI_BASE_URL", ""))
    if override:
        return override
    account_id = str(env.get("CLOUDFLARE_ACCOUNT_ID", "")).strip()
    if not account_id:
        return ""
    gateway_id = str(
        env.get("CLOUDFLARE_AI_GATEWAY_ID") or env.get("CLOUDFLARE_GATEWAY_ID") or ""
    ).strip()
    if gateway_id:
        return _GATEWAY_BASE_URL.format(account_id=account_id, gateway_id=gateway_id)
    return _DIRECT_BASE_URL.format(account_id=account_id)


def build_catalog_url(env: Mapping[str, str]) -> str:
    """Build the native catalog URL, which always uses the account API."""
    account_id = str(env.get("CLOUDFLARE_ACCOUNT_ID", "")).strip()
    if not account_id:
        return ""
    return _CATALOG_URL.format(account_id=account_id)
