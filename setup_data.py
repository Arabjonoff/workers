"""
Fixture (data_utf8.json) ni bazaga yuklaydi.
Muammo: dump ichida auth.user yozuvlari yo'q, lekin profillar userga bog'langan.
Shu skript kerakli userlarni yaratadi, keraksiz yozuvlarni (admin log, contenttype,
permission) chiqarib tashlaydi va toza fixture yuklaydi. Adminlarga parol beradi.

Ishga tushirish:  python manage.py shell < setup_data.py
"""
import json, os
import django
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
import main.models as mm

SRC = 'data_utf8.json'
CLEAN = 'data_clean.json'

# 1. contenttype/permission larni tozalash (migrate yaratganlari fixture bilan to'qnashadi)
Permission.objects.all().delete()
ContentType.objects.all().delete()

# 2. Token avtomatik yaratuvchi signalni o'chirish (fixture'dagi tokenlar bilan to'qnashmasin)
post_save.disconnect(mm.create_profile, sender=User)

# 3. Fixture'ni o'qib, kerakli user id larni yig'ish
data = json.load(open(SRC, encoding='utf-8'))
uids = set()
for o in data:
    m, f = o['model'], o['fields']
    if m in ('main.adminprofile', 'main.workerprofile'):
        uids.add(f['user'])
    elif m == 'authtoken.token':
        uids.add(f['user'])

for i in sorted(uids):
    if not User.objects.filter(id=i).exists():
        User.objects.create(id=i, username=f'user{i}', is_active=True)

# 4. Keraksiz modellarni chiqarib toza fixture yozish
skip = {'admin.logentry', 'contenttypes.contenttype', 'auth.permission'}
kept = [o for o in data if o.get('model') not in skip]
json.dump(kept, open(CLEAN, 'w'))

# 5. Yuklash
from django.core.management import call_command
call_command('loaddata', CLEAN)

# 6. Adminlarga parol berish (login: username / parol: admin123)
for ap in mm.AdminProfile.objects.select_related('user').all():
    u = ap.user
    u.is_staff = True
    u.is_superuser = True
    u.set_password('admin123')
    u.save()
    print('ADMIN ->', u.username, '/ parol: admin123')

print('Tayyor. Ishchilar:', mm.WorkerProfile.objects.count())
