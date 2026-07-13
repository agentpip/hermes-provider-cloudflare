"""Standalone Cloudflare Workers AI provider for Hermes Agent."""

from __future__ import annotations

from collections.abc import Mapping

from .profile import CloudflareProfile, build_profile

__all__ = ["CloudflareProfile", "build_profile", "register"]


def register(*_args, env: Mapping[str, str] | None = None, **_kwargs) -> CloudflareProfile:
    """Register and return the Cloudflare provider profile."""
    from providers import register_provider

    profile = build_profile(env)
    register_provider(profile)
    return profile
