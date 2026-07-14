#!/usr/bin/env python
"""Vize randevu takip - baslangic noktasi.

Kullanim:
    python run.py                 # surekli takip (nazik dongu)
    python run.py --once          # tek tur kontrol edip cikar
    python run.py --test-notify   # bildirim kanallarini test et
    python run.py --config other.yaml
"""
from __future__ import annotations

import argparse
import signal
import sys

from vizetakip.config import load_config
from vizetakip.notifier import Notifier
from vizetakip.poller import Poller
from vizetakip.state import StateStore
from vizetakip.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Vize randevu takip asistani")
    parser.add_argument("--config", default="config.yaml", help="Ayar dosyasi yolu")
    parser.add_argument("--once", action="store_true", help="Tek tur kontrol edip cik")
    parser.add_argument("--run-for", type=int, default=0, metavar="SANIYE",
                        help="Bu kadar saniye boyunca donguyle kontrol edip cik (cron/GitHub Actions icin)")
    parser.add_argument("--test-notify", action="store_true", help="Bildirimleri test et")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    notifier = Notifier(cfg.notify)

    if args.test_notify:
        notifier.send(
            "🔔 Test bildirimi",
            "Vize takip sistemi calisiyor. Bu bir testtir; gercek randevu bildirimi degil.",
            url="https://example.com",
        )
        print("Test bildirimleri gonderildi (etkin kanallara). Kontrol et.")
        return 0

    state = StateStore("state.json")
    poller = Poller(cfg, notifier, state)

    if args.once:
        poller.check_all()
        return 0

    if args.run_for > 0:
        poller.run_for(args.run_for)
        return 0

    # systemd stop/restart -> SIGTERM'i temiz kapanisa cevir
    try:
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    except (AttributeError, ValueError):
        pass

    poller.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
