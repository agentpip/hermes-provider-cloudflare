"""Cloudflare Workers AI native model-catalog helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any
from urllib.parse import urlparse, urlunparse
from urllib.request import Request

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300.0
_CACHE_MAX_ENTRIES = 32
_cache_lock = threading.Lock()
_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}


def catalog_url_from_inference_url(base_url: str) -> str | None:
    """Map a direct Workers AI inference URL to its native catalog endpoint."""
    normalized = str(base_url or "").strip().rstrip("/")
    if not normalized:
        return None
    try:
        parsed = urlparse(normalized)
        port = parsed.port
    except ValueError:
        return None
    path = parsed.path.rstrip("/")
    path_parts = path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.cloudflare.com"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or len(path_parts) != 7
        or path_parts[:4] != ["", "client", "v4", "accounts"]
        or not path_parts[4]
        or path_parts[5:] != ["ai", "v1"]
    ):
        return None
    search_path = path[: -len("/ai/v1")] + "/ai/models/search"
    return urlunparse(parsed._replace(path=search_path, params="", query="", fragment=""))


def model_ids_from_catalog(payload: Any, *, text_generation_only: bool = True) -> list[str]:
    """Extract unique inference model IDs from a native Cloudflare catalog payload."""
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
        return []

    models: list[str] = []
    seen: set[str] = set()
    for entry in payload["result"]:
        if not isinstance(entry, dict):
            continue
        task = entry.get("task")
        task_name = str(task.get("name") or "").strip() if isinstance(task, dict) else ""
        if text_generation_only and task_name.casefold() != "text generation":
            continue
        model_id = str(entry.get("name") or "").strip()
        if model_id.startswith("@cf/meta-llama/"):
            model_id = "@cf/meta/" + model_id.removeprefix("@cf/meta-llama/")
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        models.append(model_id)
    return models


def _cache_key(catalog_url: str, api_key: str) -> tuple[str, str]:
    digest = hashlib.blake2b(api_key.encode("utf-8", errors="replace"), digest_size=8)
    return catalog_url, digest.hexdigest()


def _prune_cache(now: float) -> None:
    """Drop expired entries and bound credential/account churn."""
    expired = [
        key for key, (timestamp, _models) in _cache.items() if now - timestamp >= _CACHE_TTL_SECONDS
    ]
    for key in expired:
        _cache.pop(key, None)
    while len(_cache) > _CACHE_MAX_ENTRIES:
        oldest = min(_cache, key=lambda key: _cache[key][0])
        _cache.pop(oldest, None)


def _open_catalog_url(request: Request, *, timeout: float):
    """Open a credentialed request without forwarding auth across origins."""
    from hermes_cli.urllib_security import open_credentialed_url

    return open_credentialed_url(request, timeout=timeout)


def fetch_model_ids(
    catalog_url: str,
    api_key: str,
    *,
    timeout: float = 8.0,
    opener=None,
    user_agent: str = "hermes-cli",
    force_refresh: bool = False,
) -> list[str] | None:
    """Fetch normalized text-generation model IDs from Cloudflare's catalog."""
    if not catalog_url or not api_key:
        return None

    key = _cache_key(catalog_url, api_key)
    now = time.monotonic()
    if not force_refresh:
        with _cache_lock:
            _prune_cache(now)
            cached = _cache.get(key)
            if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
                return list(cached[1])

    request = Request(
        catalog_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
    )
    open_url = opener or _open_catalog_url
    try:
        with open_url(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.debug(
            "Cloudflare catalog fetch failed for %s (%s)",
            catalog_url,
            type(exc).__name__,
        )
        return None

    models = model_ids_from_catalog(payload)
    with _cache_lock:
        _cache[key] = (now, list(models))
        _prune_cache(now)
    return models
