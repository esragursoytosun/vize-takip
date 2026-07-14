"""Son durumu diske yazar; tekrar tekrar ayni bildirimi atmayi engeller."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: str | Path = "state.json") -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                self._data = {}

    def _save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def get(self, key: str) -> dict[str, Any]:
        return self._data.get(key, {})

    def update(self, key: str, *, available: bool | None, notified_at: float | None = None) -> None:
        entry = self._data.setdefault(key, {})
        entry["available"] = available
        entry["last_checked"] = time.time()
        if notified_at is not None:
            entry["notified_at"] = notified_at
        self._save()

    def last_available(self, key: str) -> bool | None:
        return self._data.get(key, {}).get("available")

    def last_notified(self, key: str) -> float:
        return float(self._data.get(key, {}).get("notified_at", 0.0))
