# Contributing

Thank you for improving the Cloudflare Workers AI provider for Hermes Agent.

## Before starting

1. Search open and closed issues and pull requests in this repository.
2. For changes to Hermes itself, also search `NousResearch/hermes-agent` and
   read its `CONTRIBUTING.md`, `AGENTS.md`, and provider-plugin documentation.
3. Keep Cloudflare-specific behavior here. Upstream Hermes changes must be
   provider-agnostic extension points with a non-Cloudflare fixture.

## Development

Use Python 3.11 or newer and a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Set `HERMES_SOURCE` to a current Hermes checkout for integration tests:

```bash
export HERMES_SOURCE="$HOME/Software/hermes-agent"
pytest
ruff check .
ruff format --check .
python -m build
```

Tests must not call live Cloudflare APIs. Mock HTTP boundaries in unit tests.
Credentialed smoke tests are manual release gates and must never print tokens.

## Pull requests

- Use focused branches and Conventional Commit messages.
- Add behavior-contract tests before implementation.
- Keep secrets out of commits, logs, fixtures, and issue text.
- Explain compatibility implications and list the Hermes versions/commits tested.
- Preserve contributor attribution when moving or adapting prior work.
