"""Directory-install shim for Hermes model-provider discovery."""

if __package__:
    from .hermes_provider_cloudflare import register
else:  # pytest imports a repository-root __init__ as top-level
    from hermes_provider_cloudflare import register

cloudflare = register()

__all__ = ["cloudflare", "register"]
