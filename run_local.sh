#!/usr/bin/env bash
# Workers (mebel ishlab chiqarish) loyihasini mahalliy ishga tushirish.
# Ishlatish:  bash run_local.sh
set -e
cd "$(dirname "$0")"

echo ">> Virtual muhit yaratilyapti..."
python3 -m venv venv
source venv/bin/activate

echo ">> Kutubxonalar o'rnatilyapti..."
pip install --upgrade pip -q
# Eslatma: requirements.txt dagi Pillow==8.4.0 va psycopg2-binary yangi Python'da
# xato berishi mumkin. SQLite uchun psycopg2 shart emas; moslamalar biroz bo'shatilgan.
pip install -q Django==3.2.9 djangorestframework==3.12.4 dj-rest-auth==2.2.5 \
    django-cors-headers==4.3.1 python-dateutil pytz requests django-crontab Pillow

echo ">> Migratsiyalar..."
python manage.py makemigrations main dashboard api >/dev/null 2>&1 || true
python manage.py migrate

echo ">> Ma'lumotlar yuklanyapti (bir necha daqiqa olishi mumkin)..."
python manage.py shell < setup_data.py

echo ""
echo "=================================================="
echo " Server ishga tushmoqda:  http://127.0.0.1:8000/"
echo " Admin panel:            http://127.0.0.1:8000/usta/"
echo " Login: user1   Parol: admin123"
echo "=================================================="
python manage.py runserver 127.0.0.1:8000
