"""Ortak yardimcilar."""
from __future__ import annotations

import logging
import os
import sys


def setup_logging(level: str = "INFO") -> None:
    # Windows konsolu (cp1254) emoji/Unicode'da patlamasin diye UTF-8'e sabitle
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def resolve_env(value: str | None) -> str | None:
    """config'te '..._env: FOO' ile verilen adin ortam degiskeni degerini dondurur.

    Dogrudan deger de verilmisse (env'de yoksa) oldugu gibi dondurur.
    """
    if not value:
        return None
    return os.environ.get(value, value)
