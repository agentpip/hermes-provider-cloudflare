# Hermes Provider: Cloudflare Workers AI

A standalone [Hermes Agent](https://github.com/NousResearch/hermes-agent)
model-provider plugin for Cloudflare Workers AI. It keeps Cloudflare-specific
catalog, endpoint, request, and compatibility logic outside Hermes core.

> **Status:** `0.1.0` alpha. The nested-directory installation below is the
> verified path. Git-installer and pip entry-point support depend on generic
> Hermes loader fixes tracked upstream; this README does not claim they work.

## What it supports

- OpenAI-compatible chat completions on Workers AI.
- Direct account routing or Workers AI through Cloudflare AI Gateway.
- Native model discovery through `/ai/models/search`.
- Text-generation filtering and `@cf/meta-llama/` → `@cf/meta/` normalization.
- Curated agentic fallback models when catalog discovery is unavailable.
- `x-session-affinity` for same-session prefix-cache locality.
- Cloudflare reasoning payloads through Hermes' provider-profile hook.
- Versioned `hermes-cli/<version>` User-Agent.
- Standard Hermes aliases: `cloudflare`, `cloudflare-workers-ai`, `workers-ai`,
  `workersai`, `cf`, and `cf-ai`.

This plugin is not affiliated with or endorsed by Cloudflare or Nous Research.

## Requirements

- Hermes Agent with `ProviderProfile` user-plugin discovery. Tested against:
  - upstream `NousResearch/hermes-agent@bd740f203b44237dbc5c27a2de4d86ef32af4dde`;
  - Python 3.11 locally, with CI covering Python 3.11–3.13.
- A Cloudflare account with Workers AI enabled.
- A scoped API token permitted to invoke Workers AI and read the model catalog.
- Your Cloudflare account ID, unless you supply a complete inference endpoint
  override.

## Install

The verified installation location is the model-provider namespace under the
active Hermes home:

```bash
mkdir -p ~/.hermes/plugins/model-providers
git clone https://github.com/agentpip/hermes-provider-cloudflare \
  ~/.hermes/plugins/model-providers/cloudflare
```

For a named Hermes profile, clone into that profile's isolated home instead:

```bash
mkdir -p ~/.hermes/profiles/PROFILE/plugins/model-providers
git clone https://github.com/agentpip/hermes-provider-cloudflare \
  ~/.hermes/profiles/PROFILE/plugins/model-providers/cloudflare
```

Restart the active Hermes CLI, desktop backend, or gateway after installation.
Provider profiles are discovered lazily once per process.

### Why not `hermes plugins install` or pip yet?

Current Hermes main has two generic distribution gaps:

1. `hermes plugins install owner/repo` clones model-provider manifests into the
   top-level plugin directory, while provider discovery scans
   `plugins/model-providers/<name>/`.
2. Current provider discovery does not scan package entry points. This package
   already publishes the proposed provider-owned
   `hermes_agent.model_providers` registration contract, ready for the generic
   upstream loader fix.

The wheel and source distribution are built and tested as package artifacts,
but `0.1.0` documents only the installation method verified end-to-end.

## Configure

Add the secret token to the active Hermes `.env`:

```dotenv
CLOUDFLARE_WORKERS_AI_API_TOKEN=your-scoped-token
```

The current Hermes provider contract does not yet expose non-secret companion
configuration to standalone model providers, so the account identifier is also
read from the process/Hermes environment:

```dotenv
CLOUDFLARE_ACCOUNT_ID=your-account-id
```

`CLOUDFLARE_ACCOUNT_ID` is an identifier, not a secret. This compatibility
bridge can move to `config.yaml` once Hermes exposes a generic provider config
resolver.

Optional settings:

```dotenv
# Route Workers AI through an existing Cloudflare AI Gateway.
CLOUDFLARE_AI_GATEWAY_ID=your-gateway-id

# Backward-compatible alias accepted for existing setups.
# CLOUDFLARE_GATEWAY_ID=your-gateway-id

# Full inference endpoint override for proxies or controlled testing.
# CLOUDFLARE_WORKERS_AI_BASE_URL=https://example.test/v1
```

The dedicated token name is intentional. A generic `CLOUDFLARE_API_TOKEN` is
commonly present for Wrangler or Terraform; treating it as an inference token
could make Hermes auto-select Workers AI unexpectedly. Explicit generic-token
fallback can be added after Hermes has a provider eligibility hook.

## Select the provider

Use the normal Hermes model flow:

```text
/model
```

Choose **Cloudflare Workers AI**, or configure a model explicitly:

```yaml
model:
  provider: cloudflare
  name: "@cf/moonshotai/kimi-k2.6"
```

The provider also accepts `workers-ai`, `cf`, and the other aliases listed
above.

## Endpoint behavior

Inference endpoint precedence:

1. `CLOUDFLARE_WORKERS_AI_BASE_URL`.
2. AI Gateway endpoint when account ID and gateway ID are configured.
3. Direct Workers AI endpoint from account ID.
4. No endpoint: the profile remains ineligible for auth auto-detection until an
   account ID or full override is configured and Hermes is restarted.

The native catalog always uses Cloudflare's account API—even when inference is
routed through AI Gateway—so model discovery remains available.

## Upgrade and uninstall

```bash
cd ~/.hermes/plugins/model-providers/cloudflare
git pull --ff-only
```

To uninstall, remove that plugin directory and restart Hermes. No core Hermes
files are modified.

## Security

- Use a least-privilege token scoped to the required account and Workers AI.
- Never place credentials in `config.yaml`, command history, bug reports, or
  test fixtures.
- Catalog cache keys contain a short one-way token digest, never the raw token.
- Catalog redirects use Hermes' credential-safe opener, which strips
  authorization on cross-origin redirects.
- Exceptions and debug logs include endpoint context but never credentials.
- A custom base URL receives the same bearer token; only use endpoints you
  control and trust.

## Compatibility and limitations

- Live capability metadata from Cloudflare's catalog is intentionally not
  injected into Hermes' global model metadata yet. Hermes needs a generic
  provider capability hook first.
- A curated fallback list keeps the model picker usable offline, but individual
  account entitlements and model availability can differ.
- Python package artifacts exist for reproducible builds and future loader
  support; nested-directory discovery is the supported `0.1.0` install path.
- The separately proposed Cloudflare AI Gateway multi-provider backend is a
  different product surface. This plugin routes **Workers AI** through a
  gateway ID; it does not replace Hermes' providers with Cloudflare's unified
  gateway catalog.

## Origins and contributors

This repository extracts and consolidates Cloudflare work originally proposed
inside Hermes Agent. Permanent source credit:

- [#10386](https://github.com/NousResearch/hermes-agent/pull/10386) —
  [Marcelo](https://github.com/marceloeatworld), credential safeguards and
  missing-account diagnostics. Source commits `fd9dd194` and `f4d03d1d`.
- [#16398](https://github.com/NousResearch/hermes-agent/pull/16398) —
  [mchenco](https://github.com/mchenco), provider setup, AI Gateway routing,
  User-Agent, and session affinity. Source commits `3c72b0ca`, `7e7cb11c`,
  `7f045098`, and `9fc13956`.
- [#35904](https://github.com/NousResearch/hermes-agent/pull/35904) —
  [mustafabozkaya](https://github.com/mustafabozkaya), native model discovery.
  Source commit `fb7fae4c`.
- [#53105](https://github.com/NousResearch/hermes-agent/pull/53105) —
  [HimanM](https://github.com/HimanM), Cloudflare model-name normalization.
  Source commit `9ea93c8a`.
- [#58084](https://github.com/NousResearch/hermes-agent/pull/58084) —
  [agentpip](https://github.com/agentpip), consolidation, caching, filtering,
  reasoning behavior, and contract tests.

The extraction preserves source-PR and commit references rather than adding
unapproved `Co-authored-by` trailers.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). The fast local checks are:

```bash
export HERMES_SOURCE="$HOME/Software/hermes-agent"
pytest
ruff check .
ruff format --check .
python -m build
```

## License

MIT. See [LICENSE](LICENSE).
