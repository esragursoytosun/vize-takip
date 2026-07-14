# Oracle Cloud "Always Free" ile 7/24 Kurulum

Amaç: Vize takip sistemini **sonsuza kadar ücretsiz**, hiç uyumayan bir sunucuda
7/24 çalıştırmak. Bilgisayarın kapalı olsa bile çalışır; boşluk çıkınca telefonuna
Telegram bildirimi düşer.

> Kredi kartı sadece **kimlik doğrulama** için istenir. "Always Free" kaynaklardan
> ücret alınmaz. Yine de hesabı açarken **"Upgrade to Paid" yapma**, "Always Free"
> kaynakları seç.

Tahmini süre: ilk kurulum ~30-45 dk (bir kerelik). Sonrası: unut gitsin.

---

## Adım 1 — Oracle Cloud hesabı aç

1. https://www.oracle.com/cloud/free/ → **Start for free**.
2. E-posta, ülke (Turkey), telefon doğrulaması, kredi kartı doğrulaması.
3. Hesap açılınca **Oracle Cloud Console**'a giriş yap.

## Adım 2 — Ücretsiz sunucu (VM) oluştur

1. Console'da sol menü → **Compute → Instances → Create instance**.
2. **Name:** `vize-takip`
3. **Image and shape → Edit:**
   - Image: **Canonical Ubuntu 22.04** (Ubuntu seç, kurulum scripti buna göre)
   - Shape: **Always Free** etiketli olanı seç:
     - `VM.Standard.A1.Flex` (ARM, Always Free — 1 OCPU / 6 GB yeter) **veya**
     - `VM.Standard.E2.1.Micro` (AMD, Always Free)
   > Shape listesinde **"Always Free-eligible"** yazan seçeneği kullan.
4. **Add SSH keys:** "Generate a key pair for me" → **Save private key** (`.key` dosyasını
   bilgisayarına indir, ör. `C:\Users\Esra\Desktop\Projeler\oracle-key.key`). Bu dosyayı kaybetme.
5. **Networking:** varsayılan (public IP verilsin) kalsın.
6. **Create** → 1-2 dk sonra instance **Running** olur. **Public IP adresini** not al
   (ör. `123.45.67.89`).

## Adım 3 — Windows'tan sunucuya bağlan

PowerShell aç ve (kendi IP ve key yolunla):

```powershell
# anahtar dosyasi izinlerini daralt (Windows'ta bazen gerekir)
icacls "C:\Users\Esra\Desktop\Projeler\oracle-key.key" /inheritance:r /grant:r "$($env:USERNAME):(R)"

ssh -i "C:\Users\Esra\Desktop\Projeler\oracle-key.key" ubuntu@123.45.67.89
```

İlk bağlantıda "yes" yaz. Artık sunucudasın (komut satırı `ubuntu@...` olur).

## Adım 4 — Projeyi sunucuya yükle

**Bilgisayarında yeni bir PowerShell** aç (sunucudakini kapatma). Önce ağır Windows
sanal ortamını temizle (sunucu kendisi yenisini kuracak), sonra yükle:

```powershell
Remove-Item -Recurse -Force "C:\Users\Esra\Desktop\Projeler\vize-takip\.venv" -ErrorAction SilentlyContinue

scp -i "C:\Users\Esra\Desktop\Projeler\oracle-key.key" -r `
    "C:\Users\Esra\Desktop\Projeler\vize-takip" `
    ubuntu@123.45.67.89:~/
```

## Adım 5 — Tek komutla kur

Sunucudaki (SSH) pencereye dön:

```bash
cd ~/vize-takip
bash deploy/setup_oracle.sh
```

Script her şeyi kurar (Python, bağımlılıklar, 7/24 servis). Bitince sana sıradaki
komutları söyler.

## Adım 6 — Gizli bilgileri gir

```bash
nano .env
```
Doldur: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SMTP_USER`, `SMTP_PASS`,
`MALTA_SESSION_COOKIE`. (Kaydet: `Ctrl+O`, `Enter`, çık: `Ctrl+X`.)

```bash
nano config.yaml
```
- Malta isteğinin `url`'sini ve availability marker'larını gir (bu kısmı Claude senin
  için hazırlayacak — aşağıya bak).
- **Önemli:** sunucuda ekran yok, o yüzden `desktop:` altında `enabled: false` yap.
  `telegram` ve `email` açık kalsın.

## Adım 7 — Test et ve başlat

```bash
# once bildirimler calisiyor mu:
./.venv/bin/python run.py --test-notify      # telefonuna Telegram gelmeli

# 7/24 baslat:
sudo systemctl start vize-takip

# calisiyor mu / loglar:
sudo systemctl status vize-takip
sudo journalctl -u vize-takip -f             # canli log (Ctrl+C ile cik)
```

Artık sunucu 7/24 çalışıyor. Sunucu yeniden başlasa bile servis otomatik ayağa kalkar
(`Restart=always` + `enable`). Bilgisayarını kapatabilirsin.

---

## Sık kullanılan komutlar

```bash
sudo systemctl stop vize-takip        # durdur
sudo systemctl restart vize-takip     # yeniden baslat (config/.env degisince)
sudo journalctl -u vize-takip -n 50   # son 50 satir log
```

## Ayar değiştirince

`.env` veya `config.yaml`'ı `nano` ile düzenledikten sonra:
```bash
sudo systemctl restart vize-takip
```

## Kod güncellenince (Claude yeni sürüm hazırlarsa)

Bilgisayarından tekrar `scp` ile yükle, sonra sunucuda:
```bash
cd ~/vize-takip && ./.venv/bin/pip install -r requirements.txt && sudo systemctl restart vize-takip
```

---

## ⚠️ Hâlâ eksik olan tek şey: Malta'nın gerçek isteği

Bu sunucu kurulumu, sistemin **7/24 çalışmasını** sağlar. Ama sistemin Malta'da gerçek
randevu görebilmesi için hâlâ **Malta randevu sayfasının gerçek uygunluk isteğini**
(URL + Cookie + "boş/dolu" işareti) yakalaman gerekiyor:

Tarayıcıda Malta randevu sistemine gir → `F12` → **Network** → sayfayı yenile →
randevu getiren isteği bul → sağ tık → **Copy as cURL** → çıktıyı Claude'a yapıştır.
Claude `config.yaml`'ı senin için doldurur.

Bu iki iş birbirinden bağımsız: sunucuyu şimdi kurabilirsin, Malta isteğini sonra
eklersin.
