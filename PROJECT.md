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
- Bilvosita, 2026-07-17'da qo'shildi: `Turnover` (`client__company`),
  `ProductTurnover` (`product__company`), `RecipeItem` (`product__company`)

### Global (tenant tushunchasi yo'q, ataylab)
`Backup` (tizim loglari), `DateModel` (oxirgi o'zgarish vaqtlari — keshni
yangilash uchun), `SavolJavob` (FAQ).

### Retsept (BOM) — 2026-07-17'da qo'shildi
`Product.standard_price` (ixtiyoriy standart narx) va `RecipeItem`
(`product`, `material`, `mount`) — tayyor mahsulotning 1 donasi uchun
qancha xom-ashyo ketishini belgilaydi. Narx va zaxira yetarliligi
`dashboard/views.py`dagi `_material_price`/`_material_stock`/`_recipe_cost`/
`_recipe_stock_check` funksiyalari orqali hisoblanadi (`/usta/recipe/<id>/`).

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

> ⚠️ **2026-07-17**: `main/migrations/0002_recipe_item.py` qo'shildi
> (Retseptlar bo'limi uchun). Production serverga keyingi deploy qilishda
> kodni yangilagandan so'ng albatta `python manage.py migrate` ishga
> tushirilishi kerak — aks holda "Retseptlar" bo'limi `OperationalError`
> beradi (`standard_price` ustuni/`RecipeItem` jadvali bo'lmaydi).

## Kelajakda e'tibor berish kerak bo'lgan joylar

- Haqiqiy to'lov (Payme/Click) integratsiyasi yo'q — `Company.price`/`plan`
  faqat ma'lumot uchun, super-admin qo'lda boshqaradi.
- SMS yuborish (`main/funcs.py`, `dashboard/sms_sender.py`, `api/views.py`
  ichidagi `sms_send`) uchinchi-tomon `xssh.uz` API'siga bog'liq — token/ID
  qattiq kodga yozilgan, kelajakda `.env`ga ko'chirish tavsiya etiladi.
- Media fayllar (ishchi rasmlari) va PostgreSQL bazasi uchun avtomatik
  backup hali sozlanmagan.
- `Turnover.finished`/`rejected` maydonlari hozircha ishlatilmaydi — Sotuv/Olish
  bitta bosqichda darhol yakunlanadi, "qoralama → tasdiqlash" oqimi yo'q.
- Ombordan mijozsiz chiqim (yaroqsiz mahsulotni hisobdan chiqarish) hali yo'q
  — "Mahsulot chiqim" hozircha ataylab "Sotuv" bilan bir xil oqimga yo'naltirilgan.
- "Ishlab chiqarish" (`produce_recipe`) hech qanday audit-yozuv (kim, qachon
  ishlab chiqardi) qoldirmaydi — faqat `PIS.mount`larni to'g'ridan-to'g'ri
  o'zgartiradi. Kerak bo'lsa, kelajakda alohida "ishlab chiqarish tarixi"
  modeli/jurnali qo'shish mumkin.

## Mavjud dashboard bo'limlari — qisqa xarita

| Bo'lim | View (`dashboard/views.py`) | URL | Holati |
|---|---|---|---|
| Bosh sahifa | `HomePageView` | `/usta/` | ✅ |
| Ishlar ro'yxati | `WorksListView` | `/usta/works/` | ✅ |
| Ishchilar | `WorkersListView`, `WorkerProfileView` | `/usta/workers/`, `/usta/worker/<id>/` | ✅ |
| Pul berish (ishchi oyligi) | `GiveMoneyHistoryListView` | `/usta/give_money/` | ✅ |
| Jarimalar | `BugWorksView` | `/usta/bugs/` | ✅ |
| **Mijozlar** (Haridorlar/Taminotchilar/Turli shaxslar) | `ClientsView`, `ClientProfileView` | `/usta/clients/<type>/`, `/usta/client/<id>/` | ✅ (2026-07-17) |
| Mahsulotlar / Ombor | `ProductsView`, `StoragesView` | `/usta/products/`, `/usta/storages/` | ✅ (ombor qo'shish nuqsoni 2026-07-17'da tuzatildi) |
| **Kassa** (Hamyonlar, Kirim, Chiqim, Harajat) | `KassaView`, `cash_income`, `cash_outcome`, `cash_expense` | `/usta/kassa/` | ✅ (2026-07-17) |
| **Sotuv / Mahsulot kirim-chiqim** (Turnover) | `TurnoverView` | `/usta/turnover/<type>/` | ✅ (2026-07-17) |
| **Retseptlar** (BOM — narx va zaxira hisob-kitobi) | `RecipeListView`, `RecipeDetailView` | `/usta/recipes/`, `/usta/recipe/<id>/` | ✅ (2026-07-17) |

Barcha asosiy dashboard bo'limlari endi ishlaydi — sidebar'da placeholder
qolmagan.

## Bajarilgan ishlar tarixi

Har bir bajarilgan ishning batafsil yozuvi [WORK_LOG.md](WORK_LOG.md) da.
Bu yerda faqat yakunlangan yirik bosqichlar ro'yxati yuritiladi:

- **2026-07** — Tenant izolyatsiyasi to'liq qayta ishlab chiqildi (yuqoridagi
  "Tenant izolyatsiyasi" bo'limiga qarang).
- **2026-07-17** — Admin panel sidebar tekshirildi, placeholder bo'limlar
  aniqlandi.
- **2026-07-17** — **Mijozlar** bo'limi qurildi va ishga tushirildi
  (Haridorlar/Taminotchilar/Turli shaxslar — bitta `Client` modeli, `type`
  bo'yicha filtrlangan; ro'yxat, qo'shish, profil, tahrirlash, o'chirish —
  hammasi ishlaydi va test qilingan). Batafsil: `WORK_LOG.md`.
- **2026-07-17** — **Kassa** bo'limi qurildi va ishga tushirildi (Hamyonlar,
  Kirim, Chiqim, Harajat — mobil API bilan bir xil mantiq; Django shell
  orqali hisob-kitob to'g'riligi tasdiqlandi). Batafsil: `WORK_LOG.md`.
- **2026-07-17** — Mijoz profilidagi "Pul tarixi" tabi Kassa ma'lumotlariga
  ulandi (foydalanuvchi test paytida topgan kamchilik). Batafsil: `WORK_LOG.md`.
- **2026-07-17** — **Sotuv / Mahsulot kirim-chiqim (Turnover)** bo'limi
  noldan loyihalab qurildi (avval hech qanday kod yo'q edi) — zaxira
  tekshiruvi, mijoz qarz hisobi, ixtiyoriy darhol to'lov, ko'p qatorli
  savdo cheki. `Turnover`/`ProductTurnover` tenant-izolyatsiyaga ulandi.
  Batafsil: `WORK_LOG.md`.
- **2026-07-17** — **Retseptlar (BOM)** bo'limi noldan qurildi — birinchi
  marta yangi migratsiya (`0002_recipe_item.py`) qo'shildi
  (`Product.standard_price`, yangi `RecipeItem` modeli). Tayyor mahsulot
  uchun 1 donalik narx va joriy zaxira bilan necha dona tayyorlash mumkinligi
  hisoblanadi. **Production'da deploy paytida `migrate` ishga tushirish
  shart** (yuqoridagi "Deploy va production" bo'limiga qarang). Batafsil:
  `WORK_LOG.md`.
- **2026-07-17** — Ombor qo'shish nuqsoni tuzatildi (`storage.html`
  `products.html`dan noto'g'ri nusxa olingan ekan, `StoragesView`da
  `post()` yo'q edi). Endi ombor qo'shish/tahrirlash/o'chirish to'liq
  ishlaydi. Batafsil: `WORK_LOG.md`.
- **2026-07-17** — Retseptlarga **"Ishlab chiqarish"** qo'shildi — endi
  tugma bosilsa, xom-ashyo turli omborlardan avtomatik kamayadi (eng ko'p
  zaxiralidan boshlab) va tayyor mahsulot omborga qo'shiladi, zaxira
  yetmasa hech narsa o'zgarmaydi. Retseptlar bo'limi endi to'liq ishlaydigan
  aylanma (hisob-kitobdan — real ombor harakatigacha). Batafsil: `WORK_LOG.md`.
