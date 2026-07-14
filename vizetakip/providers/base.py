"""Provider (adapter) arayuzu.

Yeni bir randevu sistemi turu eklemek istersen CheckProvider'i miras al ve
check() metodunu yaz. Cikti daima bir CheckResult olmali.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CheckResult:
    """Tek bir kontrolun sonucu.

    available:
        True  -> randevu VAR
        False -> randevu yok
        None  -> bilinemedi (hata / oturum gecersiz / beklenmeyen cevap)
    """
    available: Optional[bool]
    detail: str = ""          # insana gosterilecek kisa aciklama
    needs_attention: bool = False  # or. oturum cerezi gecersiz -> kullanici mudahalesi


class CheckProvider:
    name: str = "base"

    def check(self, watcher) -> CheckResult:  # noqa: ANN001
        raise NotImplementedError
