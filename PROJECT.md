# Workers — mebel ishlab chiqarish boshqaruv tizimi (SaaS)

Bu fayl butun loyihaning arxitekturasi, modullari va ishlash mantig'ini
tasvirlaydi. Loyiha ustida ishlashni davom ettirish uchun (yoki yangi AI
agent/dasturchi kirganda) birinchi navbatda shu faylni o'qing. Server/deploy
holati uchun [DEPLOYMENT.md](DEPLOYMENT.md) ga qarang.

## Loyiha nima qiladi

Mebel ishlab chiqarish korxonalari uchun boshqaruv tizimi: ishchilarni,
ularning kunlik ishlarini, ombor/mahsulotlarni, mijozlarni, kassa va
to'lovlarni boshqarish. Loyiha **multi-tenant SaaS** sifatida qurilgan —
bitta serverda bir nechta mustaqil "korxona" (obunachi) ishlaydi, va
hech bir korxona boshqasining ma'lumotini ko'ra olmaydi.

## Arxitektura — 4 ta Django app

| App | Vazifasi | Kim uchun |
|---|---|---|
| `main` | Modellar (barcha ma'lumot bazasi sxemasi shu yerda), ishchi portali (veb) | Ishchilar (brauzer orqali) |
| `dashboard` | Admin paneli (korxona boshqaruvi) + super-admin paneli | Korxona admini va platforma egasi |
| `api` | DRF REST API | Mobil ilova (ishchi va admin uchun) |
| `config` | Django sozlamalari, URL marshrutlash | — |

Uchta mustaqil "kirish nuqtasi" bor:
1. **`/`** (root, `main` app) — ishchining o'zi kiradigan veb-portal (kunlik ish belgilash, tarix, profil)
2. **`/usta/`** (`dashboard` app) — korxona admini paneli (ishchilar, ishlar, ombor, kassa, mijozlar, hisobotlar)
3. **`/super/`** (`dashboard/super_*`) — platforma egasi paneli (korxonalarni qo'shish/bloklash/obunasini boshqarish)
4. **`/api/v1/`** (`api` app) — mobil ilova uchun REST API (worker va admin login, barcha CRUD amallar)

## Ma'lumot modeli (`main/models.py`)

### Tenant zanjiri
```
Company (korxona/obunachi)
  └── AdminProfile (1:1 User bilan) — korxona admini
        └── WorkerProfile (1:1 User bilan) — ishchi
        └── WorkCategory — ish turlari va narxlari
```

### Tenant-scoped modellar (har birida `company` FK yoki `admin`/`worker` orqali bilvosita)
- To'g'ridan-to'g'ri `company` FK: `Storage`, `Product`, `PIS`, `Client`, `Cash`,
  `Payment`, `ProductCategory`, `ProductDesign`, `OutcomeCategory`
- Bilvosita (`worker__admin__company` yoki `admin__company` orqali): `WorkerProfile`,
  `WorkCategory`, `Day`, `Work`, `BalanceHistory`, `BugWork`

### Global (tenant tushunchasi yo'q, ataylab)
`Backup` (tizim loglari), `DateModel` (oxirgi o'zgarish vaqtlari — keshni
yangilash uchun), `SavolJavob` (FAQ), `ProductTurnover`/`Turnover` (mahsulot
aylanmasi — hozircha hech qanday view/API orqali ishlatilmaydi).

### Obuna (`Company` modeli)
```python
plan          # 'trial' | 'start' | 'business' | 'premium'
price         # oylik narx (faqat ma'lumot uchun, to'lov integratsiyasi yo'q)
start_date, end_date
is_active     # qo'lda blok/ochish
has_access()  # is_active AND not is_expired — barcha joyda shu tekshiriladi
```

## Tenant izolyatsiyasi — qanday ishlaydi

Bu qism 2026-yil iyulda to'liq qayta ishlab chiqilgan (avval deyarli barcha
ma'lumot global edi — bu jiddiy xavfsizlik muammosi bo'lgan). Hozirgi
mexanizm:

- **`main/tenancy.py`** → `get_request_company(user)` — so'rov qaysi
  `Company` nomidan kelayotganini aniqlaydigan yagona funksiya (admin yoki
  ishchi uchun).
- **`main/managers.py`** → `TenantManager`/`TenantQuerySet` — har bir modelda
  `Model.TENANT_LOOKUP` orqali `Model.objects.for_company(company)`.
- **`api/mixins.py`** → `TenantScopedViewSetMixin` — barcha 10 ta DRF
  ViewSet (`api/views.py`) shundan meros oladi, `get_queryset()`/`perform_create()`
  avtomatik tenant bo'yicha filtrlaydi. Yangi ViewSet qo'shsangiz, shu mixin'ni
  albatta qo'shing va `tenant_lookup` ni to'g'ri belgilang.
- **`api/permissions.py`** → `IsActiveTenant` — global `DEFAULT_PERMISSION_CLASSES`
  (`config/settings.py`) orqali har bir API so'rovida obuna holatini tekshiradi.
- **`dashboard/decorators.py`** (`is_staff`) va **`main/decorators.py`**
  (`is_worker`) — dashboard va ishchi-portal view'larida `company.has_access()`
  tekshiradi.
- **`dashboard/middleware.py`** (`TenantAccessMiddleware`) — zaxira qatlam:
  agar biror view dekoratorni unutib qo'ysa ham, bloklangan/muddati tugagan
  tenant baribir chetlab o'tolmaydi.
- **Dashboard view'larda** (`dashboard/views.py`): har bir `.get()`/`.filter()`
  albatta `admin=request.user.admin` yoki `company=request.user.admin.company`
  bilan birga yoziladi — `get_object_or_404(Model, id=..., admin=request.user.admin)`
  patternini qo'llang (`WorkerProfileView` — namunaviy misol).

**Qoida**: yangi model yoki view qo'shganda, u albatta yuqoridagi
mexanizmlardan biriga ulanishi kerak. Tekshirish uchun:
`main/tests/test_tenant_isolation.py` ga o'xshash test yozing (pastga qarang).

## Foydalanuvchi turlari va autentifikatsiya

| Rol | Model | Login joyi | Tekshiruv |
|---|---|---|---|
| Platforma egasi (super-admin) | `User.is_superuser=True` | `/super/login/` | `super_required` (`dashboard/super_views.py`) |
| Korxona admini | `AdminProfile` (`User.is_staff=True`) | `/usta/login/` | `is_staff` (`dashboard/decorators.py`) |
| Ishchi | `WorkerProfile` | `/login/` | `is_worker` (`main/decorators.py`) |
| Mobil ilova (ishchi) | `WorkerProfile` + DRF Token | `POST /api/v1/login/` | `IsAuthenticated` + `IsActiveTenant` |
| Mobil ilova (admin) | `AdminProfile` + DRF Token | `POST /api/v1/admin/login/` | `IsAuthenticated` + `IsActiveTenant` |

Har bir `User` yaratilganda signal orqali avtomatik DRF `Token` yaratiladi
(`main/models.py` — `create_profile` signal handler).

## URL xaritasi (asosiylari)

**Dashboard (`/usta/...`, `dashboard/urls.py`)**: `""` (bosh sahifa/statistika),
`workers/`, `worker/<id>/` (ishchi profili), `works/` (ish turlari),
`give_money/` (balans to'lash), `bugs/` (jarima), `products/`, `storages/`,
`product_edit/<id>`, `product_delete/<id>`.

**Super-admin (`/super/...`, `dashboard/super_urls.py`)**: `""` (korxonalar
ro'yxati), `add/`, `edit/<id>/`, `toggle/<id>/` (blok/ochish), `renew/<id>/`
(obunani uzaytirish).

**Ishchi portali (`/...`, `main/urls.py`)**: `""` (kunlik ishlar), `works/`,
`history/`, `profile/`, `login/`.

**API (`/api/v1/...`, `api/urls.py`)**: `login/`, `admin/login/`, `today/`
(kunlik ishlar), `history_days/`, va router orqali to'liq CRUD:
`workers/`, `works/`, `products/`, `product_category/`, `product_design/`,
`storage/`, `payments/`, `clients/`, `outcome/`, `cashs/`.

## Muhim fayllar — tezkor xarita

| Fayl | Vazifasi |
|---|---|
| `main/models.py` | Butun ma'lumot bazasi sxemasi + `Company.has_access()` |
| `main/tenancy.py`, `main/managers.py` | Tenant aniqlash va scope qilish infratuzilmasi |
| `main/funcs.py` | Umumiy yordamchi funksiyalar (SMS kod, ishchi yaratish, kunlik ish hisoblash) |
| `main/cronjobs.py` | `create_day` (kunlik ish yaratish), `check_subscriptions` (obuna muddatini tekshirish) |
| `dashboard/views.py` | Admin paneli view'lari |
| `dashboard/super_views.py` | Super-admin (korxona/obuna boshqaruvi) |
| `dashboard/decorators.py`, `dashboard/middleware.py` | Admin paneli uchun ruxsat/obuna tekshiruvi |
| `api/views.py` | Barcha DRF ViewSet va API endpoint'lar |
| `api/mixins.py`, `api/permissions.py` | API uchun tenant izolyatsiyasi |
| `api/serializers.py` | DRF serializer'lar (e'tibor: yangi tenant-FK maydon qo'shsangiz `read_only_fields`ga qo'shishni unutmang) |
| `config/settings.py` | Barcha global sozlamalar, `.env` orqali production/dev farqi |
| `setup_data.py` | Test/demo ma'lumot yaratuvchi skript (`python manage.py shell < setup_data.py`) |

## Test

`main/tests/test_tenant_isolation.py` — 12 ta test: cross-tenant IDOR
himoyasi (dashboard va API), obuna muddati tugashi/uzaytirish. Ishga
tushirish:
```bash
python manage.py test main.tests.test_tenant_isolation
```
Yangi funksionallik qo'shganda, ayniqsa yangi model/ViewSet/view qo'shsangiz,
shu fayl uslubida tenant-izolyatsiya testi yozing.

## Xavfsizlik bo'yicha eslatmalar

- Har qanday yangi DRF ViewSet **albatta** `TenantScopedViewSetMixin`dan
  meros olishi kerak — aks holda cross-tenant ma'lumot sizib chiqadi
  (2026-iyuldagi audit shu sababli 10+ jiddiy zaiflik topgan edi).
- Har qanday yangi dashboard view'da obyektni ID orqali olishda albatta
  `admin=request.user.admin` yoki `company=...` filtri bilan bering —
  hech qachon `Model.objects.get(id=...)` deb yozmang.
- Yangi serializer'da `fields = '__all__'` ishlatsangiz va model'da
  `company`/`admin` FK bo'lsa, albatta `read_only_fields`ga qo'shing.
- Production sozlamalari (`SECRET_KEY`, `DEBUG`, baza) `.env` orqali —
  hech qachon kodga qattiq yozmang (`.env.example`ga qarang).

## Deploy va production

To'liq server holati, stack (nginx/gunicorn/PostgreSQL/cron), yangilash
buyruqlari va bajarilmagan ishlar — [DEPLOYMENT.md](DEPLOYMENT.md) da.

## Kelajakda e'tibor berish kerak bo'lgan joylar

- `Turnover`/`ProductTurnover` modellari hech qanday ViewSet orqali
  ochilmagan — kelajakda API qo'shilsa, `client.company`/`product.product.company`
  orqali tenant-scope qilish kerak bo'ladi.
- Haqiqiy to'lov (Payme/Click) integratsiyasi yo'q — `Company.price`/`plan`
  faqat ma'lumot uchun, super-admin qo'lda boshqaradi.
- SMS yuborish (`main/funcs.py`, `dashboard/sms_sender.py`, `api/views.py`
  ichidagi `sms_send`) uchinchi-tomon `xssh.uz` API'siga bog'liq — token/ID
  qattiq kodga yozilgan, kelajakda `.env`ga ko'chirish tavsiya etiladi.
- Media fayllar (ishchi rasmlari) va PostgreSQL bazasi uchun avtomatik
  backup hali sozlanmagan.
