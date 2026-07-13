import hermes_provider_cloudflare.profile as profile_module
from hermes_provider_cloudflare.profile import CloudflareProfile, build_profile


def test_profile_declares_provider_identity_endpoint_and_fallback_models():
    profile = build_profile(
        {
            "CLOUDFLARE_ACCOUNT_ID": "account-123",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "not-read-by-builder",
        }
    )

    assert isinstance(profile, CloudflareProfile)
    assert profile.name == "cloudflare"
    assert "workers-ai" in profile.aliases
    assert profile.api_mode == "chat_completions"
    assert profile.base_url == "https://api.cloudflare.com/client/v4/accounts/account-123/ai/v1"
    assert profile.env_vars == ("CLOUDFLARE_WORKERS_AI_API_TOKEN",)
    assert profile.supports_health_check is False
    assert profile.fallback_models
    assert all(model.startswith("@cf/") for model in profile.fallback_models)


def test_profile_adds_session_affinity_as_request_header():
    profile = build_profile({"CLOUDFLARE_ACCOUNT_ID": "account-123"})

    extra_body, top_level = profile.build_api_kwargs_extras(session_id="session-456")

    assert extra_body == {}
    assert top_level == {"extra_headers": {"x-session-affinity": "session-456"}}


def test_profile_translates_disabled_reasoning_to_cloudflare_think_flag():
    profile = build_profile({"CLOUDFLARE_ACCOUNT_ID": "account-123"})

    extra_body, top_level = profile.build_api_kwargs_extras(
        reasoning_config={"enabled": False, "effort": "none"},
        supports_reasoning=True,
    )

    assert extra_body == {
        "reasoning": {"enabled": False, "effort": "none"},
        "think": False,
    }
    assert top_level == {}


def test_profile_fetch_models_uses_native_catalog_even_with_gateway(monkeypatch):
    calls = []

    def fake_fetch(catalog_url, api_key, *, timeout, user_agent):
        calls.append((catalog_url, api_key, timeout, user_agent))
        return ["@cf/test/agentic-model"]

    monkeypatch.setattr(profile_module, "fetch_model_ids", fake_fetch)
    profile = build_profile(
        {
            "CLOUDFLARE_ACCOUNT_ID": "account-123",
            "CLOUDFLARE_AI_GATEWAY_ID": "gateway-456",
        }
    )

    assert profile.fetch_models(api_key="secret-token", timeout=3.5) == ["@cf/test/agentic-model"]
    assert calls == [
        (
            "https://api.cloudflare.com/client/v4/accounts/account-123/ai/models/search",
            "secret-token",
            3.5,
            profile.default_headers["User-Agent"],
        )
    ]


def test_profile_derives_catalog_from_runtime_direct_base_url(monkeypatch):
    calls = []

    def fake_fetch(catalog_url, api_key, *, timeout, user_agent):
        calls.append((catalog_url, api_key, timeout, user_agent))
        return ["@cf/test/runtime-model"]

    monkeypatch.setattr(profile_module, "fetch_model_ids", fake_fetch)
    profile = build_profile({})

    result = profile.fetch_models(
        api_key="secret-token",
        base_url="https://api.cloudflare.com/client/v4/accounts/runtime-account/ai/v1",
    )

    assert result == ["@cf/test/runtime-model"]
    assert calls[0][0] == (
        "https://api.cloudflare.com/client/v4/accounts/runtime-account/ai/models/search"
    )


def test_token_only_profile_is_not_eligible_for_auth_auto_detection():
    profile = build_profile({"CLOUDFLARE_WORKERS_AI_API_TOKEN": "token-without-endpoint"})

    assert profile.base_url == ""
    assert profile.env_vars == ()


def test_malformed_override_profile_is_not_eligible_for_auth_auto_detection():
    profile = build_profile(
        {
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "token-without-endpoint",
            "CLOUDFLARE_WORKERS_AI_BASE_URL": "not-a-url",
        }
    )

    assert profile.base_url == ""
    assert profile.env_vars == ()


def test_insecure_override_cannot_replace_account_derived_endpoint():
    profile = build_profile(
        {
            "CLOUDFLARE_ACCOUNT_ID": "safe-account",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "secret-token",
            "CLOUDFLARE_WORKERS_AI_BASE_URL": "http://attacker.example/v1",
        }
    )

    assert profile.base_url == ("https://api.cloudflare.com/client/v4/accounts/safe-account/ai/v1")
    assert profile.env_vars == ("CLOUDFLARE_WORKERS_AI_API_TOKEN",)
