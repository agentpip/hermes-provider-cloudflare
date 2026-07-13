"""Hermes ProviderProfile implementation for Cloudflare Workers AI."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from providers.base import ProviderProfile

from .catalog import catalog_url_from_inference_url, fetch_model_ids
from .config import build_catalog_url, build_inference_base_url

FALLBACK_MODELS = (
    "@cf/moonshotai/kimi-k2.6",
    "@cf/google/gemma-4-26b-a4b-it",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/moonshotai/kimi-k2.5",
    "@cf/nvidia/nemotron-3-120b-a12b",
    "@cf/openai/gpt-oss-120b",
    "@cf/openai/gpt-oss-20b",
    "@cf/zai-org/glm-4.7-flash",
)


def hermes_user_agent() -> str:
    """Return the Hermes versioned User-Agent with a stable fallback."""
    try:
        from hermes_cli import __version__

        return f"hermes-cli/{__version__}"
    except Exception:
        return "hermes-cli"


class CloudflareProfile(ProviderProfile):
    """Cloudflare Workers AI native catalog and OpenAI-compatible inference."""

    def __init__(self, *, catalog_url: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.catalog_url = catalog_url

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        session_id: str | None = None,
        **context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        if supports_reasoning:
            if reasoning_config is None:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
            else:
                extra_body["reasoning"] = dict(reasoning_config)
                effort = str(reasoning_config.get("effort") or "").strip().casefold()
                if effort == "none" or reasoning_config.get("enabled") is False:
                    extra_body["think"] = False

        top_level: dict[str, Any] = {}
        if session_id:
            top_level["extra_headers"] = {"x-session-affinity": str(session_id)}
        return extra_body, top_level

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Fetch the native catalog rather than probing an OpenAI /models route."""
        catalog_url = self.catalog_url or catalog_url_from_inference_url(base_url or "")
        if not api_key or not catalog_url:
            return None
        return fetch_model_ids(
            catalog_url,
            api_key,
            timeout=timeout,
            user_agent=self.default_headers.get("User-Agent", "hermes-cli"),
        )


def build_profile(env: Mapping[str, str] | None = None) -> CloudflareProfile:
    """Build a profile from a concrete environment snapshot."""
    values = os.environ if env is None else env
    base_url = build_inference_base_url(values)
    env_vars = ("CLOUDFLARE_WORKERS_AI_API_TOKEN",) if base_url else ()
    return CloudflareProfile(
        name="cloudflare",
        aliases=("cloudflare-workers-ai", "workers-ai", "workersai", "cf", "cf-ai"),
        display_name="Cloudflare Workers AI",
        description="Cloudflare Workers AI with native model discovery",
        signup_url="https://developers.cloudflare.com/workers-ai/",
        api_mode="chat_completions",
        env_vars=env_vars,
        base_url=base_url,
        catalog_url=build_catalog_url(values),
        auth_type="api_key",
        supports_health_check=False,
        supports_vision=True,
        fallback_models=FALLBACK_MODELS,
        default_headers={"User-Agent": hermes_user_agent()},
    )
