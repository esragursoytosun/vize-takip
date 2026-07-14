"""Provider kayit defteri."""
from __future__ import annotations

from .base import CheckProvider, CheckResult
from .http_generic import HttpGenericProvider

_REGISTRY: dict[str, CheckProvider] = {}


def get_provider(name: str) -> CheckProvider:
    if name not in _REGISTRY:
        if name == "http_generic":
            _REGISTRY[name] = HttpGenericProvider()
        else:
            raise ValueError(f"Bilinmeyen provider: {name!r}")
    return _REGISTRY[name]


__all__ = ["CheckProvider", "CheckResult", "get_provider"]
