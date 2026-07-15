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

## Kodni yangilash (deploy)

Har safar `master`ga yangi commit qo'shilganda, serverda:

```bash
ssh -i ~/.ssh/workers_server_key root@5.104.108.235
cd /var/www/workers.uz/app
git pull origin master
source venv/bin/activate
pip install -r requirements.txt        # yangi kutubxona qo'shilgan bo'lsa
python manage.py makemigrations main   # model o'zgargan bo'lsa
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart workers-uz.service
```

`CRONJOBS` (`config/settings.py`) o'zgartirilsa, qo'shimcha:
```bash
python manage.py crontab remove && python manage.py crontab add
```

## Hozirgi holat / bajarilmagan ishlar

- [ ] **DNS**: `workers.uz` domeni hali `45.82.176.240`ga yo'naltirilgan,
      bu serverga (`5.104.108.235`) emas. A-yozuv to'g'irlangach:
      ```bash
      certbot --nginx -d workers.uz -d www.workers.uz
      ```
      buyrug'i bilan bepul SSL (Let's Encrypt) o'rnatish mumkin (certbot
      serverda allaqachon o'rnatilgan).
- [ ] **Root parol**: birinchi deploy paytida chatda ochiq matnda yuborilgan
      edi — hali almashtirilmagan bo'lsa, serverda `passwd` orqali yangilang.
- [x] Superuser (`/super/` panel) yaratilgan — login `superadmin`, parol
      foydalanuvchiga alohida xabar qilingan (bu faylda saqlanmaydi).
      Birinchi kirishda albatta almashtiring.
- [ ] Demo/test ma'lumot (`setup_data.py`) production serverga **yuklanmagan** —
      bazada faqat super-admin bor. Haqiqiy korxonalarni `/super/` panelidan
      qo'shish kerak.
- [ ] Media fayllar (`media/`) va baza uchun hali avtomatik backup sozlanmagan.

## Muhim eslatmalar keyingi AI agent uchun

- Bu server **bo'lishilgan** — `apt`, nginx, systemd, ufw ga tegishli har
  qanday o'zgarish qilishdan oldin mavjud xizmatlarni (`zelly.uz`,
  `zelly-cafe-bot.service`) buzmasligiga ishonch hosil qiling.
- `STATIC_ROOT`/`MEDIA_ROOT` (`config/settings.py`) nisbiy yo'l
  (`'static'`, `'media'`) sifatida belgilangan — bu gunicorn'ning
  `WorkingDirectory` (`/var/www/workers.uz/app`)ga bog'liq ekanini
  unutmang, agar systemd fayldagi `WorkingDirectory`ni o'zgartirsangiz
  static/media yo'llari ham buziladi.
- `main/migrations/` va `db.sqlite3` `.gitignore`da — serverda migratsiya
  fayllari git orqali kelmaydi, har safar `makemigrations` qayta ishga
  tushiriladi (bu ataylab shunday, loyihaning mavjud konvensiyasi).
