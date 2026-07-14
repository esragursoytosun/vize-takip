"""config.yaml + .env yukleme ve dogrulama."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class PollConfig:
    base_interval_seconds: int = 120
    jitter_seconds: int = 45
    backoff_max_seconds: int = 1800
    quiet_hours: list[int] = field(default_factory=list)
    reminder_minutes: int = 30


@dataclass
class Watcher:
    name: str
    provider: str
    enabled: bool
    request: dict[str, Any]
    availability: dict[str, Any]
    open_url: str = ""

    @property
    def key(self) -> str:
        """state dosyasinda kullanilacak stabil kimlik."""
        return self.name.strip().lower().replace(" ", "_")


@dataclass
class Config:
    poll: PollConfig
    notify: dict[str, Any]
    watchers: list[Watcher]


def load_config(path: str | Path = "config.yaml") -> Config:
    # .env once yuklensin ki config icindeki *_env adlari cozulebilsin
    load_dotenv()

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"'{path}' bulunamadi. 'config.example.yaml' dosyasini 'config.yaml' "
            f"olarak kopyalayip doldur."
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    poll = PollConfig(**(raw.get("poll") or {}))
    notify = raw.get("notify") or {}

    watchers: list[Watcher] = []
    for w in raw.get("watchers") or []:
        watchers.append(
            Watcher(
                name=w["name"],
                provider=w.get("provider", "http_generic"),
                enabled=bool(w.get("enabled", True)),
                request=w.get("request") or {},
                availability=w.get("availability") or {},
                open_url=w.get("open_url", ""),
            )
        )

    cfg = Config(poll=poll, notify=notify, watchers=watchers)
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if not cfg.watchers:
        raise ValueError("config.yaml icinde en az bir 'watchers' girisi olmali.")
    if cfg.poll.base_interval_seconds < 30:
        # Nazik davranis: cok sik istek atma. Kasitli alt sinir.
        raise ValueError(
            "base_interval_seconds en az 30 olmali (sunucuyu yormamak + banlanmamak icin)."
        )
