# Changelog

All notable changes follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-13

### Added

- Standalone Hermes model-provider profile for Cloudflare Workers AI.
- Direct account and optional AI Gateway endpoint construction.
- Native `/ai/models/search` catalog discovery with text-generation filtering,
  model-ID normalization, bounded caching, and curated fallbacks.
- Credential-safe catalog redirects and secret-free failure logging.
- Endpoint eligibility guard so token-only setups cannot hijack auto-selection.
- Cloudflare reasoning payload translation.
- `x-session-affinity` support for prompt-cache locality.
- Versioned Hermes User-Agent.
- Real Hermes discovery, runtime, picker, and packaging contract tests.

### Provenance

This release extracts and consolidates work from NousResearch/hermes-agent
PRs #10386, #16398, #35904, #53105, and #58084. See README.md for contributor
and source-commit details.
