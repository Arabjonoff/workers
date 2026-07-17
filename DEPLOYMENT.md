# Workers.uz — server deploy holati

Bu fayl shu loyihaning production serverga qanday joylashtirilgani va uni
qanday boshqarish/yangilash kerakligini tasvirlaydi. Kelajakda shu loyiha
ustida ishlaydigan har qanday AI agent yoki odam avval shu faylni o'qishi
kerak — qayta kashf qilishning hojati yo'q.

## Server

- IP: `5.104.108.235` (Ubuntu 22.04)
- Domen: `workers.uz` / `www.workers.uz`
- **Bu server boshqa loyihalar bilan bo'lishiladi** (`zelly.uz` statik sayti,
  `zelly-cafe-bot` systemd xizmati, docker/containerd o'rnatilgan lekin
  ishlatilmayapti). Har qanday o'zgarish shu boshqa xizmatlarga ta'sir
  qilmasligi kerak.
- SSH kirish: `ssh -i ~/.ssh/workers_server_key root@5.104.108.235`
  (bu kalit shu loyiha uchun maxsus yaratilgan, faqat shu Mac'da saqlanadi).
  Parol orqali kirish o'chirilmagan, lekin foydalanilmaydi.

## Joylashuv (paths)

```
/var/www/workers.uz/app/          # git clone qilingan loyiha (origin/master)
/var/www/workers.uz/app/venv/     # Python virtualenv
/var/www/workers.uz/app/.env      # production sozlamalar (SECRET_KEY, DB, ALLOWED_HOSTS...)
/var/www/workers.uz/app/static/   # collectstatic natijasi
/var/www/workers.uz/app/media/    # yuklangan fayllar (ishchi rasmlari)
/var/www/workers.uz/app/workers.sock  # gunicorn unix socket
```

## Stack

- **Baza**: PostgreSQL 14 (`apt install postgresql`), baza nomi `workers`,
  foydalanuvchi `workers_user`. Parol `.env` faylida (`DB_PASSWORD`),
  serverdan tashqarida hech qayerda saqlanmagan.
- **App server**: gunicorn, systemd xizmati orqali:
  ```
  systemctl status workers-uz.service
  systemctl restart workers-uz.service
  journalctl -u workers-uz.service -f      # loglarni ko'rish
  ```
  Xizmat fayli: `/etc/systemd/system/workers-uz.service`
- **Reverse proxy**: nginx, konfiguratsiya `/etc/nginx/sites-available/workers.uz`
  (`sites-enabled`ga symlink qilingan). `/static/` va `/media/` to'g'ridan-to'g'ri
  nginx orqali, qolgani gunicorn socket'ga proxy qilinadi.
- **Cron**: `django_crontab` orqali ikkita vazifa ro'yxatdan o'tgan
  (`main.cronjobs.create_day` — kunlik 00:00, `main.cronjobs.check_subscriptions`
  — kunlik 00:05, muddati tugagan obunalarni bloklaydi). `crontab -l` orqali
  ko'rish mumkin.

## `.env` fayl tarkibi (server-only, gitga qo'shilmaydi)

```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=workers.uz,www.workers.uz,5.104.108.235
CORS_ALLOWED_ORIGINS=https://workers.uz,https://www.workers.uz
DB_ENGINE=postgresql
DB_NAME=workers
DB_USER=workers_user
DB_PASSWORD=...
DB_HOST=127.0.0.1
DB_PORT=5432
```

## CI/CD (GitHub Actions) — 2026-07-17'dan beri avtomatik

Deploy endi **qo'lda emas** — GitHub Actions orqali avtomatlashtirilgan.
Workflow fayli: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
(`Arabjonoff/workers` repo). Progressni ko'rish:
`gh run list --repo Arabjonoff/workers` yoki GitHub'da **Actions** tabi.

Bitta workflow (`CI/CD`), ikkita job:

1. **`test`** — har qanday branch'ga push va `master`ga PR'da ishga tushadi:
   - `pip install -r requirements.txt`
   - `python manage.py makemigrations --check --dry-run` (migratsiya
     yetishmasa xato beradi — model o'zgartirib, migratsiya yaratishni
     unutsangiz shu yerda ushlanadi)
   - `python manage.py check`
   - `python manage.py migrate` (SQLite, CI'ga xos, production bazasiga
     tegmaydi)
   - `python manage.py test` (`main/tests/test_tenant_isolation.py` — 12 test)
2. **`deploy`** — faqat `master`ga **push** bo'lganda va `test` job
   muvaffaqiyatli o'tgandan keyin ishga tushadi. Serverga SSH orqali
   ulanib, xuddi avvalgi qo'lda bajariladigan qadamlarni bajaradi:
   ```bash
   cd /var/www/workers.uz/app
   git fetch origin master
   git reset --hard origin/master   # serverdagi qo'lda o'zgartirilgan fayllarni ham qaytaradi
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   systemctl restart workers-uz.service
   ```
   Oxirida `https://workers.uz/` ga so'rov yuborib, sayt javob berayotganini
   tekshiradi (health check) — javob bermasa job qizil bo'lib chiqadi.

**Muhim farq**: `python manage.py makemigrations main` qadami endi **yo'q**.
Sabab — 2026-07-17'da `main/migrations/`, `dashboard/migrations/`,
`api/migrations/` gitga qo'shildi (avval `.gitignore`da edi, har muhitda
alohida generatsiya qilinardi — bu CI/CD uchun beqaror edi). Endi
migratsiya fayllari repo orqali keladi, serverda faqat `migrate`
ishlatiladi. **Yangi migratsiya kerak bo'lsa, uni lokal mashinada
(`python manage.py makemigrations main`) yaratib, commit qilib push
qiling** — serverda avtomatik yaratilmaydi.

### GitHub Secrets (repo Settings → Secrets and variables → Actions)

| Nom | Qiymat |
|---|---|
| `SSH_PRIVATE_KEY` | `~/.ssh/workers_server_key` fayl tarkibi |
| `SSH_HOST` | `5.104.108.235` |
| `SSH_USER` | `root` |
| `SSH_PORT` | `22` |

Kalit almashtirilsa yoki server o'zgarsa, shu 4 ta secret'ni yangilash kifoya
— workflow faylini o'zgartirish shart emas.

### Qo'lda deploy (faqat favqulodda holat uchun — CI/CD ishlamasa)

```bash
ssh -i ~/.ssh/workers_server_key root@5.104.108.235
cd /var/www/workers.uz/app
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate               # makemigrations kerak emas, migratsiyalar gitdan keladi
python manage.py collectstatic --noinput
systemctl restart workers-uz.service
```

`CRONJOBS` (`config/settings.py`) o'zgartirilsa, qo'shimcha (CI/CD hali bu
qadamni avtomatlashtirmagan, qo'lda bajarish kerak):
```bash
python manage.py crontab remove && python manage.py crontab add
```

## Hozirgi holat / bajarilmagan ishlar

- [x] **DNS**: `workers.uz` va `www.workers.uz` — `5.104.108.235`ga to'g'ri
      yo'naltirilgan.
- [x] **SSL**: Let's Encrypt sertifikat o'rnatilgan (`certbot --nginx`),
      HTTP→HTTPS avtomatik redirect ishlaydi, sertifikat certbot orqali
      avtomatik yangilanadi (2026-10-13 gacha amal qiladi). `nginx` config
      certbot tomonidan tahrirlangan (`/etc/nginx/sites-available/workers.uz`
      ichida `# managed by Certbot` izohli qatorlarga e'tibor bering — bu
      qatorlarni qo'lda o'chirmang).
- [x] `SECURE_PROXY_SSL_HEADER`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`
      sozlandi (`config/settings.py`) — Django endi nginx ortida ham
      so'rov HTTPS ekanini to'g'ri aniqlaydi.
- [ ] **Root parol**: birinchi deploy paytida chatda ochiq matnda yuborilgan
      edi — hali almashtirilmagan bo'lsa, serverda `passwd` orqali yangilang.
- [x] Superuser (`/super/` panel) yaratilgan — login `superadmin`, parol
      foydalanuvchiga alohida xabar qilingan (bu faylda saqlanmaydi).
      Birinchi kirishda albatta almashtiring.
- [ ] Demo/test ma'lumot (`setup_data.py`) production serverga **yuklanmagan** —
      bazada faqat super-admin bor. Haqiqiy korxonalarni `/super/` panelidan
      qo'shish kerak.
- [ ] Media fayllar (`media/`) va baza uchun hali avtomatik backup sozlanmagan.
- [x] **CI/CD**: GitHub Actions orqali sozlangan — `master`ga push testlardan
      o'tsa avtomatik production'ga deploy qiladi (yuqoridagi "CI/CD" bo'limiga
      qarang).
- [x] Migratsiyalar (`main/`, `dashboard/`, `api/migrations/`) gitga
      qo'shildi — endi barcha muhitda bir xil migratsiya tarixi.

## Muhim eslatmalar keyingi AI agent uchun

- Bu server **bo'lishilgan** — `apt`, nginx, systemd, ufw ga tegishli har
  qanday o'zgarish qilishdan oldin mavjud xizmatlarni (`zelly.uz`,
  `zelly-cafe-bot.service`) buzmasligiga ishonch hosil qiling.
- `STATIC_ROOT`/`MEDIA_ROOT` (`config/settings.py`) nisbiy yo'l
  (`'static'`, `'media'`) sifatida belgilangan — bu gunicorn'ning
  `WorkingDirectory` (`/var/www/workers.uz/app`)ga bog'liq ekanini
  unutmang, agar systemd fayldagi `WorkingDirectory`ni o'zgartirsangiz
  static/media yo'llari ham buziladi.
- `db.sqlite3` hali `.gitignore`da (lokal SQLite baza, production
  PostgreSQL ishlatadi — bog'liq emas). Lekin `main/migrations/`,
  `dashboard/migrations/`, `api/migrations/` **2026-07-17'dan beri gitga
  qo'shilgan** — avval bular ham gitignore'da edi va har muhitda alohida
  `makemigrations` bilan qayta yaratilardi. Bu CI/CD uchun beqaror edi
  (turli muhitda turli fayl nomi/mazmuni chiqishi mumkin edi), shuning
  uchun endi migratsiyalar repo orqali keladi. **Yangi migratsiya fayl
  qo'shsangiz, uni albatta commit qiling** — server endi o'zi
  `makemigrations` ishlatmaydi (yuqoridagi "CI/CD" bo'limiga qarang).
- Deploy job `git reset --hard origin/master` ishlatadi (`git pull` emas) —
  serverda qo'lda qilingan har qanday fayl o'zgarishi (masalan `static/`
  papkasidagi collectstatic natijalari) keyingi deploy'da qaytariladi.
  Serverda qo'lda kod o'zgartirmang — hamma narsa git orqali kelishi kerak.
