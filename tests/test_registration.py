import importlib


def test_package_registers_profile_through_hermes_registry(monkeypatch):
    providers = importlib.import_module("providers")
    captured = []
    monkeypatch.setattr(providers, "register_provider", captured.append)

    package = importlib.import_module("hermes_provider_cloudflare")
    profile = package.register(
        env={
            "CLOUDFLARE_ACCOUNT_ID": "account-123",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "test-token",
        }
    )

    assert captured == [profile]
    assert profile.name == "cloudflare"
