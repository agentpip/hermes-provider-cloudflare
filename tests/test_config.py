from hermes_provider_cloudflare.config import build_catalog_url, build_inference_base_url


def test_builds_direct_workers_ai_url_from_account_id():
    env = {"CLOUDFLARE_ACCOUNT_ID": "account-123"}

    assert build_inference_base_url(env) == (
        "https://api.cloudflare.com/client/v4/accounts/account-123/ai/v1"
    )


def test_explicit_workers_ai_base_url_wins_and_trailing_slash_is_removed():
    env = {
        "CLOUDFLARE_ACCOUNT_ID": "ignored-account",
        "CLOUDFLARE_WORKERS_AI_BASE_URL": "https://proxy.example.test/v1/",
    }

    assert build_inference_base_url(env) == "https://proxy.example.test/v1"


def test_invalid_or_insecure_base_url_override_is_rejected():
    invalid_urls = (
        "not-a-url",
        "ftp://proxy.example.test/v1",
        "http://proxy.example.test/v1",
        "https://token@proxy.example.test/v1",
    )

    for base_url in invalid_urls:
        env = {"CLOUDFLARE_WORKERS_AI_BASE_URL": base_url}
        assert build_inference_base_url(env) == ""


def test_builds_workers_ai_gateway_url_when_gateway_id_is_present():
    env = {
        "CLOUDFLARE_ACCOUNT_ID": "account-123",
        "CLOUDFLARE_AI_GATEWAY_ID": "gateway-456",
    }

    assert build_inference_base_url(env) == (
        "https://gateway.ai.cloudflare.com/v1/account-123/gateway-456/workers-ai/v1"
    )


def test_native_catalog_url_remains_direct_when_inference_uses_gateway():
    env = {
        "CLOUDFLARE_ACCOUNT_ID": "account-123",
        "CLOUDFLARE_AI_GATEWAY_ID": "gateway-456",
    }

    assert build_catalog_url(env) == (
        "https://api.cloudflare.com/client/v4/accounts/account-123/ai/models/search"
    )


def test_legacy_cloudflare_gateway_id_alias_is_supported():
    env = {
        "CLOUDFLARE_ACCOUNT_ID": "account-123",
        "CLOUDFLARE_GATEWAY_ID": "gateway-legacy",
    }

    assert build_inference_base_url(env) == (
        "https://gateway.ai.cloudflare.com/v1/account-123/gateway-legacy/workers-ai/v1"
    )
