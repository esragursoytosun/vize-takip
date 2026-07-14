"""Bildirim kanallari: Telegram, e-posta (SMTP), masaustu + ses."""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText

import requests

log = logging.getLogger("notify")


class Notifier:
    def __init__(self, notify_cfg: dict) -> None:
        self.cfg = notify_cfg or {}

    def send(self, title: str, message: str, url: str = "") -> None:
        """Etkin tum kanallara gonderir. Bir kanal patlarsa digerleri devam eder."""
        if self._enabled("telegram"):
            self._safe(self._telegram, title, message, url)
        if self._enabled("email"):
            self._safe(self._email, title, message, url)
        if self._enabled("desktop"):
            self._safe(self._desktop, title, message, url)

    # -- yardimcilar --------------------------------------------------------
    def _enabled(self, channel: str) -> bool:
        return bool(self.cfg.get(channel, {}).get("enabled"))

    @staticmethod
    def _safe(fn, *args) -> None:
        try:
            fn(*args)
        except Exception as exc:  # bir kanal digerlerini engellemesin
            log.warning("%s bildirimi basarisiz: %s", getattr(fn, "__name__", fn), exc)

    @staticmethod
    def _env(name: str | None) -> str | None:
        return os.environ.get(name) if name else None

    # -- kanallar -----------------------------------------------------------
    def _telegram(self, title: str, message: str, url: str) -> None:
        c = self.cfg["telegram"]
        token = self._env(c.get("bot_token_env"))
        chat_id = self._env(c.get("chat_id_env"))
        if not token or not chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID ayarlanmamis.")

        text = f"*{title}*\n{message}"
        if url:
            text += f"\n\n[Randevu sayfasini ac]({url})"
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Telegram bildirimi gonderildi.")

    def _email(self, title: str, message: str, url: str) -> None:
        c = self.cfg["email"]
        user = self._env(c.get("username_env"))
        pwd = self._env(c.get("password_env"))
        # 'to' verilmezse kendine gonder (SMTP kullanicisi). Boylece public repo'da
        # e-posta adresi durmasi gerekmez.
        to_addr = c.get("to") or user
        if not user or not pwd or not to_addr:
            raise RuntimeError("SMTP kullanici/sifre/alici ayarlanmamis.")

        body = message + (f"\n\nRandevu sayfasi: {url}" if url else "")
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = title
        msg["From"] = user
        msg["To"] = to_addr

        ctx = ssl.create_default_context()
        with smtplib.SMTP(c.get("smtp_host", "smtp.gmail.com"), int(c.get("smtp_port", 587))) as srv:
            srv.starttls(context=ctx)
            srv.login(user, pwd)
            srv.sendmail(user, [to_addr], msg.as_string())
        log.info("E-posta bildirimi gonderildi -> %s", to_addr)

    def _desktop(self, title: str, message: str, url: str) -> None:
        c = self.cfg["desktop"]
        if c.get("sound"):
            self._beep()
        try:
            from plyer import notification  # opsiyonel
            notification.notify(title=title, message=message, timeout=20)
            log.info("Masaustu bildirimi gosterildi.")
        except Exception:
            # plyer yoksa en azindan terminale bas
            log.info("MASAUSTU: %s - %s", title, message)

    @staticmethod
    def _beep() -> None:
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(880, 250)
                winsound.Beep(1320, 250)
        except Exception:
            print("\a", end="", flush=True)  # terminal zili (fallback)
