import os
import shutil
import subprocess
import sys
from pathlib import Path


def _run_contract(tmp_path, variables, script):
    project_root = Path(__file__).resolve().parents[1]
    hermes_source = Path(
        os.environ.get("HERMES_SOURCE", str(Path.home() / ".hermes" / "hermes-agent"))
    )
    plugin_parent = tmp_path / "plugins" / "model-providers"
    plugin_parent.mkdir(parents=True)
    shutil.copytree(
        project_root,
        plugin_parent / "cloudflare",
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "build", "dist", "*.egg-info", "__pycache__"
        ),
    )

    env = os.environ.copy()
    for key in list(env):
        if key.startswith("CLOUDFLARE_") or key.endswith(("_API_KEY", "_TOKEN")):
            env.pop(key)
    env.update(
        {
            "HERMES_HOME": str(tmp_path),
            "PYTHONPATH": os.pathsep.join([str(hermes_source), str(project_root)]),
            **variables,
        }
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_repository_root_is_discoverable_as_user_model_provider(tmp_path):
    result = _run_contract(
        tmp_path,
        {
            "CLOUDFLARE_ACCOUNT_ID": "account-123",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "test-token",
        },
        (
            "from providers import get_provider_profile; "
            "p=get_provider_profile('workers-ai'); "
            "assert p is not None; "
            "print(p.name, p.base_url)"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "cloudflare https://api.cloudflare.com/client/v4/accounts/account-123/ai/v1"
    )


def test_directory_plugin_resolves_runtime_credentials_and_picker_fallback(tmp_path):
    result = _run_contract(
        tmp_path,
        {
            "CLOUDFLARE_ACCOUNT_ID": "account-123",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "test-token",
        },
        (
            "from hermes_cli.auth import "
            "resolve_api_key_provider_credentials, resolve_provider; "
            "from hermes_cli.models import provider_model_ids; "
            "assert resolve_provider('workers-ai') == 'cloudflare'; "
            "c=resolve_api_key_provider_credentials('cloudflare'); "
            "assert c['api_key'] == 'test-token'; "
            "assert 'account-123' in c['base_url']; "
            "models=provider_model_ids('cloudflare'); "
            "assert models and all(m.startswith('@cf/') for m in models); "
            "print('runtime-ok', len(models))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("runtime-ok ")


def test_token_only_configuration_is_not_auto_selected(tmp_path):
    result = _run_contract(
        tmp_path,
        {"CLOUDFLARE_WORKERS_AI_API_TOKEN": "token-without-endpoint"},
        (
            "from hermes_cli.auth import AuthError, PROVIDER_REGISTRY, resolve_provider; "
            "from providers import get_provider_profile; "
            "p=get_provider_profile('cloudflare'); "
            "assert p is not None and p.env_vars == () and p.base_url == ''; "
            "assert 'cloudflare' not in PROVIDER_REGISTRY; "
            "\ntry: resolve_provider('auto'); raise AssertionError('auto-selected')"
            "\nexcept AuthError: pass"
        ),
    )

    assert result.returncode == 0, result.stderr


def test_account_only_configuration_is_not_reported_as_configured(tmp_path):
    result = _run_contract(
        tmp_path,
        {"CLOUDFLARE_ACCOUNT_ID": "account-without-token"},
        (
            "from hermes_cli.auth import AuthError, get_api_key_provider_status, resolve_provider; "
            "status=get_api_key_provider_status('cloudflare'); "
            "assert status['configured'] is False; "
            "\ntry: resolve_provider('auto'); raise AssertionError('auto-selected')"
            "\nexcept AuthError: pass"
        ),
    )

    assert result.returncode == 0, result.stderr


def test_base_url_override_works_without_account_id(tmp_path):
    result = _run_contract(
        tmp_path,
        {
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "override-token",
            "CLOUDFLARE_WORKERS_AI_BASE_URL": "https://proxy.example.test/v1",
        },
        (
            "from hermes_cli.auth import resolve_api_key_provider_credentials; "
            "c=resolve_api_key_provider_credentials('cloudflare'); "
            "assert c['api_key'] == 'override-token'; "
            "assert c['base_url'] == 'https://proxy.example.test/v1'"
        ),
    )

    assert result.returncode == 0, result.stderr


def test_malformed_base_url_override_is_not_auto_selected(tmp_path):
    result = _run_contract(
        tmp_path,
        {
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "token-without-valid-endpoint",
            "CLOUDFLARE_WORKERS_AI_BASE_URL": "not-a-url",
        },
        (
            "from hermes_cli.auth import AuthError, PROVIDER_REGISTRY, resolve_provider; "
            "from providers import get_provider_profile; "
            "p=get_provider_profile('cloudflare'); "
            "assert p is not None and p.env_vars == () and p.base_url == ''; "
            "assert 'cloudflare' not in PROVIDER_REGISTRY; "
            "\ntry: resolve_provider('auto'); raise AssertionError('auto-selected')"
            "\nexcept AuthError: pass"
        ),
    )

    assert result.returncode == 0, result.stderr


def test_insecure_override_cannot_bypass_validated_account_endpoint(tmp_path):
    result = _run_contract(
        tmp_path,
        {
            "CLOUDFLARE_ACCOUNT_ID": "safe-account",
            "CLOUDFLARE_WORKERS_AI_API_TOKEN": "secret-token",
            "CLOUDFLARE_WORKERS_AI_BASE_URL": "http://attacker.example/v1",
        },
        (
            "from hermes_cli.auth import PROVIDER_REGISTRY, "
            "resolve_api_key_provider_credentials; "
            "from providers import get_provider_profile; "
            "p=get_provider_profile('cloudflare'); "
            "c=resolve_api_key_provider_credentials('cloudflare'); "
            "assert p is not None and p.supports_health_check is False; "
            "assert PROVIDER_REGISTRY['cloudflare'].base_url_env_var == ''; "
            "assert c['base_url'] == "
            "'https://api.cloudflare.com/client/v4/accounts/safe-account/ai/v1'"
        ),
    )

    assert result.returncode == 0, result.stderr
