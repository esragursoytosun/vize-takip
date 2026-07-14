"""Nazik kontrol dongusu + degisiklik algilama.

Tasarim ilkeleri:
- Sunucuyu yormamak: base_interval + rastgele jitter, tek istek, quiet-hours.
- Banlanmamak: hata olunca ustel geri cekilme (backoff).
- Gurultuye bogmamak: sadece 'yok -> VAR' gecisinde bildirim; hala aciksa
  reminder_minutes'ta bir hatirlatma.
"""
from __future__ import annotations

import logging
import random
import time
from datetime import datetime

from .config import Config
from .notifier import Notifier
from .providers import get_provider
from .state import StateStore

log = logging.getLogger("poller")


class Poller:
    def __init__(self, cfg: Config, notifier: Notifier, state: StateStore) -> None:
        self.cfg = cfg
        self.notifier = notifier
        self.state = state
        self._consecutive_errors = 0

    # -- tek tur ------------------------------------------------------------
    def check_all(self) -> None:
        for watcher in self.cfg.watchers:
            if not watcher.enabled:
                continue
            self._check_one(watcher)

    def _check_one(self, watcher) -> None:  # noqa: ANN001
        provider = get_provider(watcher.provider)
        result = provider.check(watcher)
        prev = self.state.last_available(watcher.key)

        status = {True: "VAR ✅", False: "yok", None: "bilinemedi ⚠️"}[result.available]
        log.info("[%s] %s — %s", watcher.name, status, result.detail)

        if result.available is None:
            self._consecutive_errors += 1
            if result.needs_attention:
                self._maybe_attention(watcher, result.detail)
            return

        self._consecutive_errors = 0

        newly_available = result.available and prev is not True
        still_available_reminder = (
            result.available and prev is True and self._reminder_due(watcher.key)
        )

        if newly_available or still_available_reminder:
            self._notify_available(watcher, result.detail)
            self.state.update(watcher.key, available=True, notified_at=time.time())
        else:
            self.state.update(watcher.key, available=result.available)

    # -- bildirimler --------------------------------------------------------
    def _notify_available(self, watcher, detail: str) -> None:  # noqa: ANN001
        title = f"🟢 RANDEVU AÇILDI: {watcher.name}"
        msg = f"{detail}\nHemen gir ve elinle randevunu al!"
        self.notifier.send(title, msg, watcher.open_url)

    def _maybe_attention(self, watcher, detail: str) -> None:  # noqa: ANN001
        """Oturum gecersiz gibi kullanici mudahalesi gereken durumlar; saatte 1 uyar."""
        key = f"{watcher.key}::attention"
        if time.time() - self.state.last_notified(key) < 3600:
            return
        title = f"⚠️ Mudahale gerekli: {watcher.name}"
        self.notifier.send(title, detail, watcher.open_url)
        self.state.update(key, available=None, notified_at=time.time())

    def _reminder_due(self, key: str) -> bool:
        gap = self.cfg.poll.reminder_minutes * 60
        return (time.time() - self.state.last_notified(key)) >= gap

    # -- zamanlama ----------------------------------------------------------
    def next_sleep_seconds(self) -> float:
        p = self.cfg.poll
        if self._consecutive_errors > 0:
            # ustel backoff: base * 2^errors, jitter'li, tavani backoff_max
            backoff = min(p.base_interval_seconds * (2 ** self._consecutive_errors),
                          p.backoff_max_seconds)
            return backoff + random.uniform(0, p.jitter_seconds)
        return p.base_interval_seconds + random.uniform(-p.jitter_seconds, p.jitter_seconds)

    def in_quiet_hours(self, now: datetime | None = None) -> bool:
        q = self.cfg.poll.quiet_hours
        if not q or len(q) != 2:
            return False
        now = now or datetime.now()
        start, end = q
        h = now.hour
        if start <= end:
            return start <= h < end
        return h >= start or h < end  # gece yariisini gecen aralik

    # -- cron / GitHub Actions modu ----------------------------------------
    def run_for(self, seconds: float) -> None:
        """Belirtilen sure boyunca donguyle kontrol eder, sonra cikar.

        GitHub Actions gibi zamanlanmis ortamlar icin: is her 5 dk'da bir tetiklenir,
        her tetikte bu metod ~4.5 dk boyunca ~75 sn araliklarla bakar. Boylece
        sunucu olmadan, ucretsiz, ~dakika-alti etkin kontrol elde edilir.
        """
        log.info("Cron modu: ~%d sn boyunca kontrol edilecek.", int(seconds))
        deadline = time.monotonic() + seconds
        while True:
            if not self.in_quiet_hours():
                self.check_all()
            remaining = deadline - time.monotonic()
            if remaining <= 30:  # bir sonraki kontrole yer kalmadi
                break
            time.sleep(max(30.0, min(self.next_sleep_seconds(), remaining)))
        log.info("Cron turu bitti.")

    # -- surekli dongu ------------------------------------------------------
    def run_forever(self) -> None:
        log.info("Takip basladi. Ctrl+C ile durdurabilirsin.")
        active = [w.name for w in self.cfg.watchers if w.enabled]
        log.info("Izlenen: %s", ", ".join(active) or "(hicbiri etkin degil!)")
        while True:
            try:
                if self.in_quiet_hours():
                    sleep_s = 900  # sessiz saatte 15 dk'da bir uyan, kontrol etme
                    log.info("Sessiz saat; %d sn uyunuyor.", sleep_s)
                else:
                    self.check_all()
                    sleep_s = max(30.0, self.next_sleep_seconds())
                    log.info("Sonraki kontrol ~%d sn sonra.", int(sleep_s))
                time.sleep(sleep_s)
            except KeyboardInterrupt:
                log.info("Durduruldu. Gorusuruz!")
                return
            except Exception as exc:  # dongu asla olmesin
                self._consecutive_errors += 1
                log.exception("Beklenmeyen hata: %s", exc)
                time.sleep(min(self.cfg.poll.backoff_max_seconds, 60 * self._consecutive_errors))
