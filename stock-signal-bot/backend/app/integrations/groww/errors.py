"""Errors raised while using the read-only Groww integration."""


class GrowwIntegrationError(RuntimeError):
    """Raised when Groww authentication, transport, or response validation fails."""
