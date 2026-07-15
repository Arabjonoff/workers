"""
Tenant-aware namunaviy ma'lumotlarni bazaga yozadi (ikkita mustaqil korxona).
Ishga tushirish:  python manage.py shell < setup_data.py
"""
from datetime import date, timedelta
from django.contrib.auth.models import User
import main.models as mm

PASSWORD = 'admin123'


def make_company(name, phone, plan, price, days, username):
    company = mm.Company.objects.create(
        name=name, phone=phone, plan=plan, price=price,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=days) if days else None,
    )
    user = User.objects.create(username=username, first_name=name, is_staff=True)
    user.set_password(PASSWORD)
    user.save()
    admin = mm.AdminProfile.objects.create(user=user, company=company)
    return company, admin


def make_worker(admin, username, first_name, last_name, phone):
    user = User.objects.create(username=username, first_name=first_name, last_name=last_name)
    user.set_password(PASSWORD)
    user.save()
    return mm.WorkerProfile.objects.create(
        user=user, admin=admin, phone=phone, birth='2000-01-01', address='Toshkent'
    )


c1, a1 = make_company('Sifat Mebel', '+998901112233', 'business', 500000, 30, 'user1')
c2, a2 = make_company('Novvot Mebel', '+998932223344', 'trial', 0, 14, 'user34')

for company, admin, prefix, phone_base in [(c1, a1, 'sifat', 901234560), (c2, a2, 'novvot', 901234570)]:
    cat = mm.WorkCategory.objects.create(name='Yig`ish', admin=admin, price=15000, type='dona')
    w1 = make_worker(admin, f'{prefix}_ishchi1', 'Ali', 'Aliyev', phone_base + 1)
    w2 = make_worker(admin, f'{prefix}_ishchi2', 'Vali', 'Valiyev', phone_base + 2)
    w1.works.add(cat)
    w2.works.add(cat)

    storage = mm.Storage.objects.create(company=company, name='Asosiy ombor', type=1)
    pcat = mm.ProductCategory.objects.create(company=company, name="Yog'och")
    product = mm.Product.objects.create(company=company, name='Fanera', type=1, category=pcat, m_type=1)
    mm.PIS.objects.create(company=company, product=product, mount=100, start_mount=100, storage=storage)

    client = mm.Client.objects.create(company=company, name=f'{prefix.title()} mijoz', type=1)
    mm.Cash.objects.create(company=company, name='Asosiy kassa', main=True, mount=1000000, start_mount=1000000)
    mm.OutcomeCategory.objects.create(company=company, name='Kommunal')

    print(f'ADMIN -> {admin.user.username} / parol: {PASSWORD}  ({company.name})')

print('Tayyor. Companies:', mm.Company.objects.count(), 'Workers:', mm.WorkerProfile.objects.count())
