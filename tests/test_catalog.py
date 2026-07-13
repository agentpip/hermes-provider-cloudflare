import logging

import hermes_provider_cloudflare.catalog as catalog_module
from hermes_provider_cloudflare.catalog import (
    catalog_url_from_inference_url,
    fetch_model_ids,
    model_ids_from_catalog,
)


def test_maps_direct_inference_url_to_native_catalog_url():
    assert (
        catalog_url_from_inference_url(
            "https://api.cloudflare.com/client/v4/accounts/account-123/ai/v1"
        )
        == "https://api.cloudflare.com/client/v4/accounts/account-123/ai/models/search"
    )


def test_catalog_url_derivation_rejects_insecure_or_ambiguous_native_urls():
    invalid_urls = (
        "http://api.cloudflare.com/client/v4/accounts/account-123/ai/v1",
        "https://token@api.cloudflare.com/client/v4/accounts/account-123/ai/v1",
        "https://api.cloudflare.com:8443/client/v4/accounts/account-123/ai/v1",
        "https://api.cloudflare.com/client/v4/accounts//ai/v1",
    )

    assert all(catalog_url_from_inference_url(url) is None for url in invalid_urls)


def test_catalog_models_are_filtered_deduplicated_and_normalized():
    payload = {
        "result": [
            {
                "name": "@cf/meta-llama/llama-3.1-8b-instruct",
                "task": {"name": "Text Generation"},
            },
            {
                "name": "@cf/meta-llama/llama-3.1-8b-instruct",
                "task": {"name": "Text Generation"},
            },
            {
                "name": "@cf/baai/bge-large-en-v1.5",
                "task": {"name": "Text Embeddings"},
            },
            {"name": "@cf/mistral/mistral-small", "task": {"name": "Text Generation"}},
            "invalid-entry",
        ]
    }

    assert model_ids_from_catalog(payload) == [
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistral/mistral-small",
    ]


def test_fetch_model_ids_uses_bearer_auth_and_hermes_user_agent():
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return (
                b'{"result":[{"name":"@cf/meta-llama/test-model",'
                b'"task":{"name":"Text Generation"}}]}'
            )

    def opener(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    models = fetch_model_ids(
        "https://api.cloudflare.com/client/v4/accounts/acct/ai/models/search",
        "secret-token",
        opener=opener,
        user_agent="hermes-cli/test",
        force_refresh=True,
    )

    assert models == ["@cf/meta/test-model"]
    request, timeout = requests[0]
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert request.get_header("User-agent") == "hermes-cli/test"
    assert timeout == 8.0


def test_default_fetch_uses_hermes_credential_safe_opener(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"result":[]}'

    def safe_opener(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(
        "hermes_cli.urllib_security.open_credentialed_url",
        safe_opener,
    )
    result = fetch_model_ids(
        "https://api.cloudflare.com/client/v4/accounts/acct/ai/models/search",
        "secret-token",
        force_refresh=True,
    )

    assert result == []
    assert len(requests) == 1


def test_fetch_failure_does_not_log_a_token_from_exception_text(caplog):
    def opener(_request, *, timeout):
        raise RuntimeError(f"request failed token={'very-secret-token'} timeout={timeout}")

    with caplog.at_level(logging.DEBUG, logger=catalog_module.__name__):
        result = fetch_model_ids(
            "https://api.cloudflare.com/client/v4/accounts/acct/ai/models/search",
            "very-secret-token",
            opener=opener,
            force_refresh=True,
        )

    assert result is None
    assert "very-secret-token" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_fetch_model_ids_reuses_cached_result_without_another_request():
    catalog_module._cache.clear()
    request_count = 0

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"result":[{"name":"@cf/test/cached","task":{"name":"Text Generation"}}]}'

    def opener(_request, *, timeout):
        nonlocal request_count
        request_count += 1
        assert timeout == 8.0
        return Response()

    url = "https://api.cloudflare.com/client/v4/accounts/cache-test/ai/models/search"
    first = fetch_model_ids(url, "cache-token", opener=opener)
    second = fetch_model_ids(url, "cache-token", opener=opener)

    assert first == second == ["@cf/test/cached"]
    assert request_count == 1
    assert all("cache-token" not in key for key in catalog_module._cache)


def test_catalog_cache_prunes_expired_entries(monkeypatch):
    catalog_module._cache.clear()
    catalog_module._cache.update(
        {
            ("https://expired.example/one", "digest-1"): (0.0, ["one"]),
            ("https://expired.example/two", "digest-2"): (1.0, ["two"]),
        }
    )
    monkeypatch.setattr(catalog_module.time, "monotonic", lambda: 1_000.0)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"result":[]}'

    result = fetch_model_ids(
        "https://api.cloudflare.com/client/v4/accounts/new/ai/models/search",
        "new-token",
        opener=lambda _request, *, timeout: Response(),
        force_refresh=True,
    )

    assert result == []
    assert len(catalog_module._cache) == 1


def test_catalog_cache_evicts_oldest_entry_at_capacity(monkeypatch):
    catalog_module._cache.clear()
    for index in range(catalog_module._CACHE_MAX_ENTRIES):
        catalog_module._cache[(f"https://catalog.example/{index}", f"digest-{index}")] = (
            900.0 + index,
            [str(index)],
        )
    oldest_key = ("https://catalog.example/0", "digest-0")
    monkeypatch.setattr(catalog_module.time, "monotonic", lambda: 1_000.0)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"result":[]}'

    result = fetch_model_ids(
        "https://api.cloudflare.com/client/v4/accounts/new/ai/models/search",
        "new-token",
        opener=lambda _request, *, timeout: Response(),
        force_refresh=True,
    )

    assert result == []
    assert len(catalog_module._cache) == catalog_module._CACHE_MAX_ENTRIES
    assert oldest_key not in catalog_module._cache


def test_catalog_cache_hit_at_capacity_does_not_evict_an_entry(monkeypatch):
    catalog_module._cache.clear()
    cached_url = "https://api.cloudflare.com/client/v4/accounts/cached/ai/models/search"
    cached_key = catalog_module._cache_key(cached_url, "cached-token")
    catalog_module._cache[cached_key] = (900.0, ["@cf/test/cached"])
    for index in range(1, catalog_module._CACHE_MAX_ENTRIES):
        catalog_module._cache[(f"https://catalog.example/{index}", f"digest-{index}")] = (
            900.0 + index,
            [str(index)],
        )
    original_keys = set(catalog_module._cache)
    monkeypatch.setattr(catalog_module.time, "monotonic", lambda: 1_000.0)

    result = fetch_model_ids(cached_url, "cached-token")

    assert result == ["@cf/test/cached"]
    assert set(catalog_module._cache) == original_keys
