#!/usr/bin/env bash
# ============================================================================
#  Vize Takip - Oracle Cloud (veya herhangi bir Ubuntu sunucu) kurulum scripti
#  Sunucuya baglandiktan sonra proje klasorunun icinde SU sekilde calistir:
#      bash deploy/setup_oracle.sh
#  Idempotent: tekrar tekrar calistirmak guvenli.
# ============================================================================
set -euo pipefail

# proje kok dizinine gec (bu script deploy/ altinda)
cd "$(dirname "$0")/.."
PROJECT_DIR="$PWD"
echo ">> Proje dizini: $PROJECT_DIR"

echo ">> 1/5  Sistem paketleri kuruluyor (python3, venv, pip)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip
else
    echo "!! Desteklenmeyen paket yoneticisi. Ubuntu imaji onerilir." >&2
fi

echo ">> 2/5  Sanal ortam olusturuluyor (temiz)..."
rm -rf .venv                       # kopyalanmis Windows venv'i varsa sil
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt -q

echo ">> 3/5  Ayar dosyalari hazirlaniyor..."
[ -f config.yaml ] || cp config.example.yaml config.yaml
[ -f .env ] || cp .env.example .env

echo ">> 4/5  systemd servisi yaziliyor..."
SERVICE_PATH=/etc/systemd/system/vize-takip.service
sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Vize Randevu Takip
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python run.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vize-takip >/dev/null 2>&1

echo ">> 5/5  Kurulum tamam."
echo ""
echo "SIMDI SIRASIYLA:"
echo "  1) Gizli bilgileri gir:   nano .env        (Telegram token, SMTP, cookie)"
echo "  2) Ayarlari gir:          nano config.yaml (Malta URL + desktop.enabled: false)"
echo "  3) Bildirimleri test et:  ./.venv/bin/python run.py --test-notify"
echo "  4) 7/24 baslat:           sudo systemctl start vize-takip"
echo "  5) Loglari izle:          sudo journalctl -u vize-takip -f"
