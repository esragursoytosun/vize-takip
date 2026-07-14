# Vize Randevu Takip Sistemi

Vize randevu sayfasını **nazik aralıklarla** kontrol eden ve boş randevu açıldığı anda
**Telegram + e-posta + masaüstü ses** ile haber veren bir takip asistanı.

> **Felsefe / Etik sınır**
> Bu araç randevuyu **senin yerine ALMAZ**. Sadece **haber verir**; randevuyu her zaman
> insan (sen) alır. CAPTCHA atlatmaz, bot korumasını kırmaz, sunucuyu yormaz.
> Senin zaten giriş yapabildiğin bir sayfaya, agresif botlardan çok daha seyrek bakar.
> Bu sayede hem etik kalırsın hem de IP/hesabın banlanmaz — yani gerçekten randevu alabilirsin.

---

## Nasıl çalışır?

1. Sen tarayıcında randevu sistemine normal şekilde giriş yaparsın.
2. Giriş yaptığın oturumun **çerezini (cookie)** bir kere kopyalayıp `.env` dosyasına koyarsın.
3. Program o oturumla, belirlediğin aralıkta (ör. 2 dakikada bir + rastgele gecikme)
   randevu sayfasına bakar.
4. "Randevu yok" → "Randevu VAR" geçişini yakaladığı an sana 3 kanaldan da bildirim atar
   (doğrudan booking linkiyle). Sen girip elinle alırsın.

Oturum çerezi zamanla geçersiz olur; program çerez geçersizse seni uyarır, sen yenilersin.

---

## Kurulum

```powershell
cd "C:\Users\Esra\Desktop\OMNI_CORP\Output\yazilim\vize-takip"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.yaml config.yaml
copy .env.example .env
```

Sonra `config.yaml` ve `.env` dosyalarını kendine göre doldur (aşağıda anlatılıyor).

Çalıştır:

```powershell
python run.py
```

Tek seferlik test (tek tur bakıp çıkar, bildirim mantığını denemek için):

```powershell
python run.py --once
```

Bildirim kanallarını test et (gerçek randevu beklemeden Telegram/e-posta/ses çalışıyor mu):

```powershell
python run.py --test-notify
```

---

## 1) Telegram kurulumu (en hızlı bildirim — önerilir)

1. Telegram'da **@BotFather**'a yaz → `/newbot` → bir isim ver → sana bir **bot token** verir.
2. Kendi oluşturduğun bota bir mesaj at ("merhaba" yeter).
3. Chat ID'ni öğren: tarayıcıda şunu aç
   `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   Dönen JSON içinde `"chat":{"id":123456789}` → o sayı senin **chat_id**'in.
4. `.env` dosyasına `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` yaz.

## 2) E-posta (SMTP) kurulumu

Gmail için: Google hesabında **2 adımlı doğrulama** açık olmalı, sonra
**Uygulama Şifresi** (App Password) oluştur ve onu `SMTP_PASS`'e koy (normal şifreni DEĞİL).
`.env`: `SMTP_USER`, `SMTP_PASS`, alıcı adresi `config.yaml`'da.

## 3) Masaüstü + ses

Windows'ta ek kurulum gerekmez (winsound kullanılır). İstersen daha güzel bildirim balonu
için `pip install plyer` (opsiyonel, requirements'ta var).

---

## Oturum çerezini (cookie) nasıl alırım?

1. Tarayıcıda randevu sistemine giriş yap.
2. `F12` → **Network** sekmesi → sayfayı yenile.
3. Randevu tarihlerini/uygunluğu getiren isteği bul (genelde `slots`, `availability`,
   `calendar`, `appointment` gibi bir isim geçer, tipi `XHR/Fetch`).
4. O isteğe sağ tıkla → **Copy → Copy as cURL**. İçindeki `Cookie:` satırını `.env`'e koy.
   İstek URL'sini ve gerekiyorsa başlıkları `config.yaml`'daki `watchers` altına yaz.

> Doğru isteği bulamıyorsan bana "Copy as cURL" çıktısını yapıştır; ben `config.yaml`'ı
> senin yerine dolduruyum.

---

## Yeni ülke eklemek

`config.yaml` içindeki `watchers:` listesine yeni bir blok ekle — kod değişikliği gerekmez.
Her ülke/konsolosluk/vize tipi ayrı bir "watcher"dır ve tek tek açılıp kapatılabilir.

## Dosya yapısı

```
vize-takip/
├── run.py                 # başlangıç noktası (CLI)
├── config.yaml            # senin ayarların (git'e girmez)
├── .env                   # gizli anahtarlar/çerezler (git'e girmez)
├── requirements.txt
└── vizetakip/
    ├── config.py          # config + .env yükleme
    ├── state.py           # son durumu hatırlar (tekrar bildirim atmaz)
    ├── poller.py          # nazik döngü + değişiklik algılama
    ├── notifier.py        # Telegram / e-posta / masaüstü
    ├── utils.py
    └── providers/
        ├── base.py        # adapter arayüzü
        └── http_generic.py# config'ten sürülen genel HTTP kontrolcü
```
