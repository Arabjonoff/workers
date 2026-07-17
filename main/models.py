from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from rest_framework.authtoken.models import Token
from datetime import datetime, date

from .managers import TenantManager


PLAN_TYPES = (
    ('trial', 'Sinov'),
    ('start', 'Start'),
    ('business', 'Biznes'),
    ('premium', 'Premium'),
)


class Company(models.Model):
    """Ijarachi (tenant) — bitta mebel korxonasi. Super-admin qo'shadi."""
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)   # bloklangan bo'lsa kira olmaydi
    created = models.DateTimeField(auto_now_add=True)

    plan = models.CharField(max_length=20, choices=PLAN_TYPES, default='trial')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)  # bo'sh = muddatsiz

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        return bool(self.end_date and self.end_date < date.today())

    @property
    def days_remaining(self):
        return (self.end_date - date.today()).days if self.end_date else None

    def has_access(self):
        return self.is_active and not self.is_expired


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='admins')
    date = models.DateTimeField(auto_now_add=True)
    gave_money = models.IntegerField(default=0)
    workers_money = models.IntegerField(default=0)
    bugs_money = models.IntegerField(default=0)

    code = models.BigIntegerField(default=0)

    def __str__(self):
        return self.user.username


class WorkerProfile(models.Model):
    TENANT_LOOKUP = 'admin__company'
    objects = TenantManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker')
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, related_name='workers')
    date = models.DateTimeField(auto_now_add=True)
    balance = models.IntegerField(default=0)
    got_balance = models.IntegerField(default=0)
    bugs_sum = models.IntegerField(default=0)
    image = models.FileField(upload_to='profile_images/', blank=True, null=True)

    birth = models.DateField(blank=True)
    phone = models.PositiveIntegerField()
    home_phone = models.PositiveIntegerField(blank=True, null=True)
    address = models.CharField(blank=True, max_length=250)
    active = models.BooleanField(default=True)

    code = models.BigIntegerField(default=0)

    works = models.ManyToManyField('main.WorkCategory', blank=True, related_name='category_workers')

    def __str__(self):
        return self.user.username
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.worker = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class WorkCategory(models.Model):
    TENANT_LOOKUP = 'admin__company'
    objects = TenantManager()

    WORK_TYPES = (
        ("dona","dona"),
        ("metr","metr"),
    )

    name = models.CharField(max_length=200)
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, related_name='work_categories')
    date = models.DateTimeField(auto_now_add=True)
    price = models.IntegerField()
    type = models.CharField(choices=WORK_TYPES, max_length=4)

    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.work_category = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class Day(models.Model):
    TENANT_LOOKUP = 'worker__admin__company'
    objects = TenantManager()

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='days')
    date = models.DateTimeField(auto_now_add=True)
    sum = models.IntegerField(default=0)
    sent_balance = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return str(self.date)


class Work(models.Model):
    TENANT_LOOKUP = 'day__worker__admin__company'
    objects = TenantManager()

    category = models.ForeignKey(WorkCategory, on_delete=models.SET_NULL, related_name='works', null=True)
    active = models.BooleanField(default=True)
    day = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='theworks')
    count = models.IntegerField(default=0)
    length = models.FloatField(default=0)
    sum = models.IntegerField(default=0)

    def __str__(self):
        return str(self.category)


class BalanceHistory(models.Model):
    TENANT_LOOKUP = 'worker__admin__company'
    objects = TenantManager()

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='balance_history')
    cash = models.ForeignKey('Cash', on_delete=models.CASCADE, related_name='worker_payments', blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    got_sum = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.date)
    

class BugWork(models.Model):
    TENANT_LOOKUP = 'worker__admin__company'
    objects = TenantManager()

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='bugs')
    date = models.DateTimeField(auto_now_add=True)
    price = models.IntegerField(default=0)
    info = models.CharField(max_length=350)

    def __str__(self):
        return self.info


class Backup(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    info = models.TextField()

    def __str__(self):
        return str(self.date.strftime('%Y-%m-%d ^ %T'))


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)


class ProductCategory(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='product_categories')
    name = models.CharField(max_length=450)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.product_category = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class ProductDesign(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='product_designs')
    name = models.CharField(max_length=450)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

PRODUCT_TYPES = (
    (1, 'Hom ashyo'),
    (2, 'Yarim tayyor'),
    (3, 'Tayyor'),
    (4, 'Boshqa')
)

MTYPES = (
    (1, 'dona'),
    (2, 'metr'),
    (3, 'sm'),
    (4, 'tonna'),
    (5, 'kg'),
    (6, 'gram'),
)


class Storage(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='storages')
    name = models.CharField(max_length=450)
    type = models.IntegerField(choices=PRODUCT_TYPES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=450)
    type = models.IntegerField(choices=PRODUCT_TYPES)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, blank=True, null=True)
    design = models.ForeignKey(ProductDesign, on_delete=models.CASCADE, blank=True, null=True)
    m_type = models.IntegerField(choices=MTYPES)
    standard_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name


class RecipeItem(models.Model):
    """Retsept (BOM): tayyor mahsulot uchun 1 donaga qancha hom-ashyo ketishini belgilaydi."""
    TENANT_LOOKUP = 'product__company'
    objects = TenantManager()

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipe_items')
    material = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='used_in_recipes')
    mount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('product', 'material')

    def __str__(self):
        return f'{self.product.name}: {self.mount} x {self.material.name}'


class PIS(models.Model): # Product in storage
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='pis_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pis')
    mount = models.DecimalField(max_digits=12, decimal_places=1)
    start_mount = models.DecimalField(max_digits=12, decimal_places=1)
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.mount} {self.product} in {self.storage.name}'
         

CURRENCY_TYPES = (
    (1, 'UZS'),
    (2, 'USD'),
    (3, 'RUB')
)

CLIENT_TYPES = (
    (1, 'Haridor'),
    (2, 'Taminotchi'),
    (3, 'Turli shaxslar')
)
    

class Client(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=250)
    type = models.IntegerField(choices=CLIENT_TYPES)
    phone1 = models.CharField(max_length=15, blank=True, null=True)
    phone2 = models.CharField(max_length=15, blank=True, null=True)
    card_number = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=830, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Cash(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cashes')
    name = models.CharField(max_length=250)
    currency = models.IntegerField(choices=CURRENCY_TYPES, default=1)
    main = models.BooleanField(default=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='cashs', blank=True, null=True)
    mount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_mount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.cash = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class OutcomeCategory(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='outcome_categories')
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Payment(models.Model):
    TENANT_LOOKUP = 'company'
    objects = TenantManager()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    date = models.DateTimeField(blank=True, null=True)
    mount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.IntegerField(choices=CURRENCY_TYPES, default=1)
    type = models.IntegerField(choices=(
        (1, 'Kirim'),
        (2, 'Chiqim'),
        (3, 'Harajat'),
        (4, 'Oylik')
    ))
    comment = models.TextField(default='Izoh yo`q')

    category = models.ForeignKey(OutcomeCategory, on_delete=models.CASCADE, blank=True, null=True)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, blank=True, null=True)
    
    client_cash = models.ForeignKey(Cash, on_delete=models.CASCADE, blank=True, null=True, related_name='client_cashs')
    client_before = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    client_after = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    cash = models.ForeignKey(Cash, on_delete=models.CASCADE, blank=True, null=True)
    cash_before = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cash_after = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    for_product = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.comment
    

class ProductTurnover(models.Model):
    TENANT_LOOKUP = 'product__company'
    objects = TenantManager()

    product = models.ForeignKey(PIS, on_delete=models.CASCADE)
    mount = models.DecimalField(max_digits=12, decimal_places=1)
    status = models.IntegerField(choices=(
        (1, 'created'),
        (2, 'recieved'),
        (3, 'rejected')
    ))
    price = models.DecimalField(max_digits=12, decimal_places=2)
    bonus_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus_mount = models.DecimalField(max_digits=12, decimal_places=1, default=0)

    @property
    def total_price(self):
        return round((self.price - self.bonus_price) * self.mount, 2)

    def __str__(self):
        return self.product.product.name
    

class Turnover(models.Model): # product turnover
    TENANT_LOOKUP = 'client__company'
    objects = TenantManager()

    type = models.IntegerField(choices=(
        (1, 'Sotish'),
        (2, 'Olish')
    ))
    products = models.ManyToManyField(ProductTurnover, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    finished = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    finished_date = models.DateTimeField(blank=True, null=True)
    rejected_date = models.DateTimeField(blank=True, null=True)

    @property
    def status(self):
        all = self.products.all().count()
        created = self.products.filter(status=1).count()
        received = self.products.filter(status=2).count()
        rejected = self.products.filter(status=3).count()
        p = (all / 100) if all > 0 else 100

        data = {
            'created': round((created / p) if created > 0 else 0, 1),
            'received': round((received / p) if received > 0 else 0, 1),
            'rejected': round((rejected / p) if rejected > 0 else 0, 1)
        }
        return data
    

class DateModel(models.Model):
    worker = models.DateTimeField(blank=True, null=True)
    work_category = models.DateTimeField(blank=True, null=True)
    cash = models.DateTimeField(blank=True, null=True)
    product_category = models.DateTimeField(blank=True, null=True)
    product_design = models.DateTimeField(blank=True, null=True)
    storage = models.DateTimeField(blank=True, null=True)
    outcome_category = models.DateTimeField(blank=True, null=True)
    client = models.DateTimeField(blank=True, null=True)


class SavolJavob(models.Model):
    q = models.CharField(max_length=1500)
    a = models.CharField(max_length=1500)

    def __str__(self):
        return self.q