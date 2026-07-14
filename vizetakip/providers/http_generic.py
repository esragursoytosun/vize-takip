"""Config'ten surulen genel HTTP kontrolcu.

Cogu vize sistemi icin kod yazmaya gerek yok: config.yaml'da istegin URL'sini,
basliklarini, cerezini ve "randevu var mi" kararinin nasil verilecegini tanimlarsin.
"""
from __future__ import annotations

import logging
import os

import requests
from jsonpath_ng import parse as jsonpath_parse

from .base import CheckProvider, CheckResult

log = logging.getLogger("provider.http")


class HttpGenericProvider(CheckProvider):
    name = "http_generic"

    def __init__(self) -> None:
        self._session = requests.Session()

    def check(self, watcher) -> CheckResult:  # noqa: ANN001
        req = watcher.request
        url = req.get("url")
        if not url or "ORNEK-DOMAIN" in url:
            return CheckResult(
                available=None,
                detail="request.url ayarlanmamis (config.yaml).",
                needs_attention=True,
            )

        headers = dict(req.get("headers") or {})
        cookies = _load_cookies(req.get("cookies_env"))

        try:
            resp = self._session.request(
                method=req.get("method", "GET").upper(),
                url=url,
                headers=headers,
                cookies=cookies,
                data=req.get("body"),
                timeout=20,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return CheckResult(available=None, detail=f"Baglanti hatasi: {exc}")

        # Oturum gecersizse cogu sistem login sayfasina yonlendirir / 401-403 doner
        if resp.status_code in (401, 403):
            return CheckResult(
                available=None,
                detail=f"Oturum gecersiz olabilir (HTTP {resp.status_code}). Cookie'yi yenile.",
                needs_attention=True,
            )
        if resp.status_code >= 400:
            return CheckResult(available=None, detail=f"HTTP {resp.status_code}")

        return _evaluate(watcher.availability, resp)


def _load_cookies(cookies_env: str | None) -> dict[str, str]:
    """.env'deki 'Cookie:' satirini (isim=deger; ...) sozluge cevirir."""
    if not cookies_env:
        return {}
    raw = os.environ.get(cookies_env, "")
    if not raw or "buraya_tarayicidan" in raw:
        return {}
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def _evaluate(spec: dict, resp: requests.Response) -> CheckResult:
    mode = (spec.get("type") or "text").lower()

    if mode == "json":
        try:
            data = resp.json()
        except ValueError:
            return CheckResult(
                available=None,
                detail="JSON bekleniyordu ama cevap JSON degil (oturum/URL yanlis olabilir).",
                needs_attention=True,
            )
        return _evaluate_json(spec, data)

    # ---- text / html modu ----
    text = resp.text.lower()
    unavailable = [m.lower() for m in spec.get("unavailable_markers") or []]
    available = [m.lower() for m in spec.get("available_markers") or []]

    if available and any(m in text for m in available):
        return CheckResult(available=True, detail="Uygun tarih isareti bulundu.")
    if unavailable and any(m in text for m in unavailable):
        return CheckResult(available=False, detail="Randevu yok isareti bulundu.")
    if available and not any(m in text for m in available):
        return CheckResult(available=False, detail="Uygun tarih isareti yok.")
    return CheckResult(
        available=None,
        detail="Metinde ne 'var' ne 'yok' isareti eslesti; markerlari gozden gecir.",
    )


def _evaluate_json(spec: dict, data) -> CheckResult:
    # Yontem 1: sayaci kontrol et
    count_path = spec.get("json_count_path")
    if count_path:
        matches = [m.value for m in jsonpath_parse(count_path).find(data)]
        total = 0
        for v in matches:
            if isinstance(v, (int, float)):
                total += v
            elif isinstance(v, list):
                total += len(v)
            elif v:
                total += 1
        min_count = int(spec.get("min_count", 1))
        return CheckResult(
            available=total >= min_count,
            detail=f"{total} uygun slot (esik: {min_count}).",
        )

    # Yontem 2: truthy path
    avail_path = spec.get("json_available_path")
    if avail_path:
        matches = [m.value for m in jsonpath_parse(avail_path).find(data)]
        truthy = [m for m in matches if m]
        return CheckResult(
            available=len(truthy) > 0,
            detail=f"{len(truthy)} adet uygun kayit.",
        )

    return CheckResult(
        available=None,
        detail="availability icin json_count_path veya json_available_path tanimlanmali.",
        needs_attention=True,
    )
