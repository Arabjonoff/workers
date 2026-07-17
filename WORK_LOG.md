# Work Log — Workers loyihasi

Bu faylga har bir bajarilgan ish alohida yozuv sifatida qo'shiladi (eng
yangisi tepada). Loyihaning umumiy holati va kelajakdagi ishlar uchun
[PROJECT.md](PROJECT.md) ga qarang.

---

## 2026-07-17 — Retseptlar: "Ishlab chiqarish" (avtomatik ombordan ayirish)

**Nima qilindi:** Retsept sahifasiga (`/usta/recipe/<id>/`) "Ishlab
chiqarish" kartasi qo'shildi — nechta dona va qaysi omborga qo'shilishini
kiritib tasdiqlansa:
1. Zaxira oldindan tekshiriladi (`_recipe_stock_check`) — yetarli bo'lmasa,
   **hech narsa o'zgarmaydi**, aniq qaysi xom-ashyo qancha yetmasligi
   xabar qilinadi.
2. Yetarli bo'lsa, har bir xom-ashyo turli omborlardagi (`PIS`) zaxiralardan
   **eng ko'p zaxirali ombordan boshlab** ketma-ket kamaytiriladi
   (`_consume_material`) — foydalanuvchi qaysi ombordan olishni tanlashi
   shart emas, avtomatik.
3. Tayyor mahsulot tanlangan omborga qo'shiladi — agar shu mahsulot uchun
   o'sha omborda `PIS` allaqachon bo'lsa, songa qo'shiladi (dublikat
   yaratilmaydi), bo'lmasa yangi yaratiladi.
4. Butun amal `transaction.atomic()` ichida — birortasi xato bersa, hech
   narsa qisman saqlanmaydi.

**Yangi/o'zgartirilgan fayllar:** `dashboard/views.py`
(`_consume_material`, `produce_recipe`, `RecipeDetailView.get`ga
`storages` context), `dashboard/urls.py` (`recipe/<id>/produce/`),
`templates/dashboard/recipe_detail.html` ("Ishlab chiqarish" kartasi).

**Test qilindi:** bitta xom-ashyo (Fanera3) ikkita omborda (5 va 100 dona)
sozlandi, retsept 1:3 (1 Shkaf = 3 Fanera3). 100 dona ishlab chiqarishga
urinilganda (300 kerak, 105 bor) — to'g'ri rad etildi, aniq kamomad (195)
ko'rsatildi, hech narsa o'zgarmadi. 30 dona ishlab chiqarilganda (90 kerak)
— eng katta ombordan (100 donalik) kamaytirildi (100→10), kichik ombor
(5 dona) tegilmadi — to'g'ri. Yana 1 dona ishlab chiqarilganda, endi
kattaroq bo'lgan (10 dona) ombordan kamaytirildi (10→7) — ustuvorlik
mantiqi to'g'ri ishladi. Tayyor mahsulot PIS'i bir marta yaratilib, keyingi
ishlab chiqarishda songa to'g'ri qo'shildi (31 = 30+1), dublikat PIS
yaratilmadi.

---

## 2026-07-17 — Ombor qo'shish nuqsoni tuzatildi

**Muammo:** `templates/dashboard/storage.html` butunlay `products.html`dan
noto'g'ri nusxa olingan ekan — "Mahsulot qo'shish" sarlavhasi, `name/type/
storage/mount/mtype` maydonlari, tahrirlash/o'chirish tugmalari
`/usta/product_edit/`, `/usta/product_delete/`ga (PIS obyektiga) ishora
qilardi — Storage (ombor) modeliga umuman mos emas edi. `StoragesView`da
ham faqat `get()` bor edi, `post()` yo'q edi — shu sabab forma "ishlamaydi"
deb ko'ringan.

**Nima qilindi:**
- `StoragesView.post()` qo'shildi — yangi ombor (`Storage.name`, `.type`)
  yaratadi.
- `edit_storage`, `delete_storage` (soft-delete) funksiyalari qo'shildi.
- `storage.html` to'liq qayta yozildi — endi to'g'ridan-to'g'ri `Storage`
  modeliga mos (nomi, turi, shu ombordagi mahsulot turlari soni), boshqa
  bo'limlar (Mijozlar/Kassa) bilan bir xil zamonaviy uslubda (`soft-card`,
  `tbl-modern`, modal orqali tahrirlash/o'chirish).

**Yangi/o'zgartirilgan fayllar:** `dashboard/views.py` (`StoragesView.post`,
`edit_storage`, `delete_storage`), `dashboard/urls.py` (2 ta yangi path),
`templates/dashboard/storage.html` (to'liq qayta yozildi).

**Test qilindi:** ombor qo'shildi ("Yangi Ombor") → ro'yxatda ko'rindi →
tahrirlandi ("Yangilangan Ombor", turi o'zgartirildi) → o'chirildi →
ro'yxatdan yo'qoldi. Boshqa sahifalar (bosh sahifa, Mahsulotlar, Kassa,
Turnover, Mijozlar, Retseptlar) hamon 200 qaytarishi tekshirildi —
regressiya yo'q.

---

## 2026-07-17 — Retseptlar (BOM) bo'limi qurildi — yangi migratsiya bilan

**Kontekst:** Foydalanuvchining haqiqiy muammosi: "1 dona tayyor mebel uchun
qancha xom-ashyo ketadi va narxi qancha", va "hozirgi ombordagi xom-ashyo
bilan N dona mebel yasashga yetadimi, yoki nechtasiga yetadi". Loyihada bu
tushuncha (qaysi tayyor mahsulot qanday xom-ashyodan tayyorlanadi) umuman
yo'q edi — birinchi marta noldan model darajasida qo'shildi.

**Foydalanuvchi bilan aniqlashtirilgan qarorlar:**
1. Xom-ashyo narxi: **standart narx bo'lsa undan, bo'lmasa oxirgi
   "Mahsulot kirim" (Olish) narxidan** (avtomatik fallback).
2. Joylashuvi: **alohida "Retseptlar" sidebar bo'limi** (mahsulot profiliga
   emas) — ro'yxat + har bir mahsulot uchun tahrirlash/hisoblash sahifasi.

**Yangi migratsiya (bu safar DB sxemasi o'zgardi):**
`main/migrations/0002_recipe_item.py` — ikkita o'zgarish:
- `Product.standard_price` (ixtiyoriy, ondalik) — xom-ashyoning "standart
  narxi", Mahsulotlar bo'limida (qo'shish/tahrirlash formasida) kiritiladi.
- Yangi model `RecipeItem` (`product`, `material`, `mount`) — 1 dona
  `product` uchun qancha `material` kerakligi. `TENANT_LOOKUP='product__company'`
  bilan tenant-izolyatsiyaga ulangan (boshidanoq to'g'ri qurildi).

**Muhim: production serverda deploy paytida albatta ishga tushirish kerak:**
```bash
python manage.py migrate
```
(Avvalgi bosqichlar — Mijozlar/Kassa/Turnover — migratsiya talab qilmagan
edi, chunki mavjud modellardan foydalangan. Bu birinchi haqiqiy schema
o'zgarishi shu sessiyada.)

**Biznes-mantiq (`dashboard/views.py`):**
- `_material_price(material, company)` — standart narx yoki oxirgi Olish
  narxi (`ProductTurnover.objects.filter(..., turnover__type=2)` orqali).
- `_material_stock(material, company)` — shu xom-ashyoning barcha
  omborlardagi (`PIS`) jami zaxirasi.
- `_recipe_cost(product, company)` — 1 dona narxini hisoblaydi, narxi
  nomalum xom-ashyolar ro'yxatini alohida qaytaradi (xato bermaydi).
- `_recipe_stock_check(product, company, count)` — berilgan `count` uchun
  har bir xom-ashyo yetarlimi (jadval) + **joriy zaxira bilan MAKSIMAL
  nechta dona tayyorlash mumkinligini** (`min` orqali barcha xom-ashyolar
  bo'yicha) hisoblaydi — bu foydalanuvchining ikkinchi savoliga to'g'ridan
  javob.

**Sahifalar:**
- `/usta/recipes/` — barcha retsepti belgilangan mahsulotlar ro'yxati
  (narxi, hom-ashyo soni, joriy zaxira bilan necha dona chiqishi), + yangi
  retsept ochish uchun mahsulot tanlash.
- `/usta/recipe/<product_id>/` — retseptni tahrirlash (dinamik qatorlar,
  JS orqali), "1 dona narxi" va "necha dona chiqadi" kartalari, va "N dona
  uchun tekshirish" formasi (har bir xom-ashyo bo'yicha yetarli/yetarsiz
  jadvali, kamomad miqdori bilan).
- Mahsulotlar sahifasiga (`products.html`) "Standart narx" maydoni
  qo'shildi (qo'shish formasi + tahrirlash modali + jadval ustuni).

**Yangi/o'zgartirilgan fayllar:** `main/models.py` (`Product.standard_price`,
`RecipeItem`), `main/migrations/0002_recipe_item.py`, `dashboard/urls.py`,
`dashboard/views.py` (`RecipeListView`, `RecipeDetailView`, yordamchi
funksiyalar, `ProductsView`/`edit_pis`ga `standard_price`),
`templates/dashboard/recipes.html`, `templates/dashboard/recipe_detail.html`,
`templates/dashboard/products.html`, `templates/dashboard/wrapper.html`.

**Test qilindi (toza bazada, migratsiya qo'llanilgan holda):**
Xom-ashyo "Fanera2" (standart narx 20,000, 100 dona) va "Vint" (narxsiz,
500 dona), tayyor mahsulot "Shkaf" yaratildi. Retsept: 1 Shkaf = 3 Fanera2
+ 20 Vint. Natijalar: Vint narxi nomalumligi to'g'ri ko'rsatildi; "necha
dona chiqadi" = 25 (min(100÷3=33, 500÷20=25) — to'g'ri); count=10 so'ralganda
"yetarli", count=30 so'ralganda Vint uchun "yetmaydi (−100)" — barchasi
qo'lda hisoblangan kutilgan natijalarga mos keldi. Boshqa barcha sahifalar
(bosh sahifa, Kassa, Turnover, Mijozlar, Mahsulotlar, Ombor) hamon 200
qaytarayotgani tekshirildi — regressiya yo'q.

**Kelajakda e'tibor:**
- Retsept faqat 1 bosqichli (xom-ashyo → tayyor mahsulot); ko'p bosqichli
  ishlab chiqarish (masalan "yarim tayyor" oraliq mahsulotlar retsepti)
  hozircha qo'llab-quvvatlanmaydi.
- Ishlab chiqarish tasdiqlangach xom-ashyoni omborda AVTOMATIK kamaytirish
  (retsept asosida "ishlab chiqarildi" tugmasi) hali yo'q — hozircha faqat
  hisob-kitob/tekshiruv, haqiqiy hisobdan chiqarish "Mahsulot chiqim"
  (Turnover) orqali qo'lda qilinadi.

---

## 2026-07-17 — Sotuv / Mahsulot kirim-chiqim (Turnover) bo'limi qurildi

**Kontekst:** `Turnover`/`ProductTurnover` modellari loyihada oldindan bor
edi, lekin hech qanday API yoki dashboard kodi ularni ishlatmasdi — bu
safar butun biznes-oqimni noldan loyihalash kerak edi (mavjud namuna yo'q
edi, Mijozlar/Kassa bosqichlaridan farqli o'laroq).

**Foydalanuvchi bilan aniqlashtirilgan qarorlar** (`AskUserQuestion` orqali):
1. Pul mantig'i — **"Hoziroq to'landi" checkbox ixtiyoriy**: belgilanmasa,
   faqat mijoz qarz/kredit hisobi (`client_cash`) yoziladi; belgilansa,
   qo'shimcha ravishda haqiqiy Kassa to'lovi ham amalga oshadi.
2. Bitta tranzaksiyada **bir nechta mahsulot qatori** (savdo cheki kabi,
   JS orqali dinamik qator qo'shish/o'chirish).

**Xavfsizlik (migratsiyasiz):** `Turnover` (`TENANT_LOOKUP='client__company'`)
va `ProductTurnover` (`TENANT_LOOKUP='product__company'`) modellariga
`TenantManager` va `TENANT_LOOKUP` qo'shildi — bu sof Python darajasidagi
o'zgarish (DB sxemasiga tegmaydi), lekin endi bu ikkala model ham loyihaning
umumiy tenant-izolyatsiya mexanizmiga ulangan (avval PROJECT.md'da
"kelajakda e'tibor" sifatida belgilangan muammo hal qilindi).

**Biznes-mantiq (`TurnoverView`, `dashboard/views.py`):**
- Sidebar'dagi 3 punkt bitta model ustiga qurilgan: **Sotuv** (Moliya) va
  **Mahsulot chiqim** (Ombor) ikkalasi ham `Turnover.type=1` ("Sotish")ga,
  **Mahsulot kirim** (Ombor) `Turnover.type=2` ("Olish")ga yo'naltiriladi —
  `ClientsView`dagi kabi bitta view, `type` URL parametri orqali.
- Har bir qator uchun `ProductTurnover` yaratiladi, `PIS.mount` (ombordagi
  zaxira) mos ravishda kamaytiriladi (Sotish) yoki oshiriladi (Olish).
  Sotishda **zaxira yetarli emasligi tekshiriladi** — yetmasa, butun
  tranzaksiya rad etiladi (hech narsa yozilmaydi), xato xabarida qaysi
  mahsulot va qancha mavjudligi ko'rsatiladi.
- Mijozning qarz/kredit hisobi (`client_cash`) yangilanadi: Sotishda
  `+= jami_summa` (mijoz qarzi oshadi), Olishda `-= jami_summa` (bizning
  taminotchiga qarzimiz oshadi) — Kassa bosqichidagi Kirim/Chiqim belgisi
  bilan bir xil, izchil ishora tizimi.
- "Hoziroq to'landi" belgilansa, xuddi Kassa'dagi Kirim/Chiqim bilan bir xil
  mantiq ishlaydi — buning uchun `cash_income`/`cash_outcome`dagi umumiy
  kodni `_record_client_payment()` funksiyasiga chiqarib, uni ham Kassa, ham
  Turnover shu funksiyani chaqiradigan qilib refaktor qildim (ikkala joyda
  bir xil hisob-kitob kafolatlanadi).

**Yangi/o'zgartirilgan fayllar:**
- `main/models.py` — `Turnover`, `ProductTurnover`ga `TENANT_LOOKUP`/`TenantManager`
- `dashboard/urls.py` — `turnover/<type>/` path
- `dashboard/views.py` — `TurnoverView`, `_with_totals`, `_record_client_payment`
  (refaktor qilingan umumiy funksiya), `cash_income`/`cash_outcome` shu
  funksiyani ishlatadigan qilib qayta yozildi
- `templates/dashboard/turnover.html` — yangi (dinamik qator qo'shish JS bilan)
- `templates/dashboard/client_detail.html` — "Mahsulot tarixi" tabi ulandi
- `templates/dashboard/wrapper.html` — Sotuv/Mahsulot kirim/Mahsulot chiqim
  havolalari ulandi

**Test qilindi (toza bazada, Django shell orqali tasdiqlab):**
mahsulot (Stol, 10 dona) va mijoz (Aziz Haridor) yaratildi → 1000 dona
sotishga urinildi → to'g'ri rad etildi ("omborda yetarli emas (mavjud: 10)"),
hech narsa o'zgarmadi → 3 dona x 50,000 so'mdan, "Hoziroq to'landi" bilan
sotildi → natijalar: ombor 10→7, mijoz qarzi 150,000 (sotuvdan) − 150,000
(to'lovdan) = 0, hamyon balansi +150,000 — barchasi kutilganidek. Mijoz
profilidagi "Mahsulot tarixi" tabida yozuv (Sotuv belgisi, summa, mahsulot
nomi modal ichida) to'g'ri ko'rindi.

**Kelajakda e'tibor:**
- `Turnover.finished`/`rejected` maydonlari hozircha ishlatilmaydi — bu
  MVP bitta bosqichli (darhol yakunlanadigan) oqim, "qoralama → tasdiqlash"
  ish jarayoni yo'q. Kerak bo'lsa keyin qo'shiladi.
- Ombordan chiqim (yaroqsiz mahsulotni hisobdan chiqarish, mijozsiz)
  hozircha yo'q — "Mahsulot chiqim" ataylab "Sotuv" bilan bir xil oqimga
  yo'naltirildi (ikkalasi ham mijozga sotish/berish degani).
- `storage.html`dagi ombor qo'shish formasi ishlamaydi — `StoragesView`da
  faqat `get()` bor, `post()` yo'q (bu Turnover ishi bilan bog'liq emas,
  test paytida tasodifan topilgan eski nuqson, alohida tuzatilishi kerak).

---

## 2026-07-17 — Mijoz profilidagi "Pul tarixi" tabi ulandi

**Nima uchun:** foydalanuvchi (Muhammadjon) test qildi — Kassa'da mijozga
Kirim qilingandan so'ng, o'sha mijozning profiliga kirganda "Pul tarixi"
hali placeholder ekanini payqadi. Bu WORK_LOG'da "kelajakda" deb belgilangan
edi — endi ulandi.

**Nima qilindi:**
- `ClientProfileView.get()` — endi `Payment.objects.filter(client_cash__client=client, type__in=[1,2])`
  orqali shu mijozga tegishli barcha Kirim/Chiqim yozuvlarini oladi,
  shuningdek `client.cashs` (sub-hisoblar, valyuta bo'yicha) balansini ham beradi.
- `client_detail.html` — "Pul tarixi" tabidagi placeholder olib tashlandi,
  o'rniga: joriy balans kartalari (valyuta bo'yicha) + to'lovlar jadvali
  (sana, turi, hamyon, summa, to'lovdan keyingi balans, izoh).

**Fayllar:** `dashboard/views.py` (`ClientProfileView.get`),
`templates/dashboard/client_detail.html`.

**Test qilindi:** toza bazada "Sifat" nomli Haridor qo'shildi, Kassa'dan
unga 150,000 so'm Kirim qilindi, profilga kirilganda yozuv (summasi, izohi,
"Kirim" belgisi bilan) to'g'ri ko'rindi.

**Kelajakda e'tibor:** "Mahsulot tarixi" tabi hamon placeholder —
Sotuv/Turnover bosqichida ulanadi.

---

## 2026-07-17 — Kassa bo'limi qurildi (Hamyonlar, Kirim, Chiqim, Harajat)

**Nima qilindi:**
- Modellar (`Cash`, `Payment`, `OutcomeCategory`) va mavjud mobil API mantiqi
  (`api/views.py` — `CashViewSet`, `PaymentsViewSet.add`/`outcome`) o'rganildi.
  Web tomon shu mantiqni **aynan takrorlaydi** — ikki tomon (mobil/web)
  hisob-kitobda bir xil natija bersin deb ataylab shunday qilindi.
- Aniqlandi: `Cash` modeli ikki xil vazifada ishlatiladi — (1) `main=True`
  haqiqiy kassalar/hamyonlar, (2) `main=False, client=<Mijoz>` — har bir
  mijoz uchun avtomatik yaratiladigan sub-hisob (qarz/kredit kuzatuvi).
- `KassaView` (ro'yxat sahifasi), `add_cash`, `add_outcome_category`,
  `cash_income` (Kirim), `cash_outcome` (Chiqim), `cash_expense` (Harajat)
  view/funksiyalari yozildi.
- `templates/dashboard/kassa.html` — hamyon kartalari, 4 ta tab (Kirim /
  Chiqim / Harajat / Tarix), 2 ta modal (hamyon qo'shish, turkum qo'shish).
- Sidebar (`wrapper.html`): "Kassa" havolasi `/usta/kassa/`ga ulandi.
  "Sotuv" hozircha ataylab ulanmagan — chunki bu haqiqiy mahsulot sotish
  (`Turnover` modeli) talab qiladi, keyingi bosqichga qoldirildi; sidebar'da
  "Tez orada" belgisi bilan ko'rsatildi (bosilmaydigan holatda), foydalanuvchi
  chalkashmasligi uchun.
- "Oylik" (`Payment.type=4`) Kassa bo'limiga kirmaydi — u allaqachon
  "Pul berish" (Ishchilar bo'limi) orqali ishlaydi, ataylab qo'shilmadi.

**Yangi/o'zgartirilgan fayllar:**
- `dashboard/urls.py` — 6 ta yangi path (`kassa/`, `kassa/add_cash/`,
  `kassa/add_category/`, `kassa/income/`, `kassa/outcome/`, `kassa/expense/`)
- `dashboard/views.py` — `KassaView`, `add_cash`, `add_outcome_category`,
  `cash_income`, `cash_outcome`, `cash_expense`, yordamchi
  `_get_or_create_client_cash`, `_parse_mount`
- `templates/dashboard/kassa.html` — yangi
- `templates/dashboard/wrapper.html` — sidebar yangilandi

**Test qilindi (lokal server, toza baza bilan, Django shell orqali tekshirib):**
Hamyon qo'shildi (500,000 UZS) → mijoz qo'shildi → Kirim qilindi (100,000) →
natija Django shell'da tasdiqlandi: hamyon balansi 600,000 (to'g'ri), mijoz
sub-hisobi avtomatik yaratilgan va balansi -100,000 (to'g'ri), `Payment`
yozuvi barcha `before`/`after` maydonlari bilan to'g'ri saqlangan. Alohida
sessiyada Chiqim va Harajat (turkum bilan) ham sinovdan o'tkazilib, kutilgan
summalar chiqdi (1,000,000 + 200,000 − 50,000 − 30,000 = 1,120,000 — mos keldi).

**Kelajakda e'tibor:** "Sotuv" — `Turnover`/`ProductTurnover` bosqichida
quriladi, o'sha safar `Payment.for_product=True` mantig'i ham ulanadi
(hozir Kirim/Chiqim formalarida `for_product` doim `False`).

---

## 2026-07-17 — Mijozlar bo'limi qurildi (Haridorlar/Taminotchilar/Turli shaxslar)

**Nima qilindi:**
- Aniqlandi: sidebar'dagi "Haridorlar", "Taminotchilar", "Turli shaxslar" —
  uchta alohida narsa emas, bitta `Client` modeli, `type` maydoni bo'yicha
  filtrlangan (`CLIENT_TYPES`: 1=Haridor, 2=Taminotchi, 3=Turli shaxslar),
  API'dagi `ClientsViewSet`/`ClientSerializer` bilan bir xil mantiq.
- Bitta `ClientsView` (ro'yxat + qo'shish) va `ClientProfileView` (profil +
  tahrirlash) klasslari yozildi — uchta menyu punkti shu bitta view'ga
  `type` parametri orqali yo'naltiriladi (`ProductsView` patterniga mos).
- `delete_client` — soft-delete (`is_active=False`), `edit_pis`/`delete_pis`
  patterniga mos.
- Mijoz profil sahifasi (`/usta/client/<id>/`) `WorkerProfileView` patterniga
  o'xshab tablar bilan qurildi: **Ma'lumotlar** (to'liq ishlaydi, tahrirlash
  mumkin), **Pul tarixi** va **Mahsulot tarixi** — hozircha placeholder
  ("keyingi bosqichda ulanadi" xabari bilan), keyingi Kassa va
  Sotuv/Turnover bosqichlarida to'ldiriladi.
- Sidebar'dagi 3 ta havola (`templates/dashboard/wrapper.html`) haqiqiy
  URL'larga ulandi (`/usta/clients/1|2|3/`), active-state tekshiruvi
  qo'shildi.

**Yangi/o'zgartirilgan fayllar:**
- `dashboard/urls.py` — 3 ta yangi path (`clients/<type>/`, `client/<id>/`,
  `client_delete/<id>`)
- `dashboard/views.py` — `ClientsView`, `ClientProfileView`, `delete_client`,
  `CLIENT_TYPE_NAMES`
- `templates/dashboard/clients.html` — yangi (ro'yxat + qo'shish formasi + qidiruv)
- `templates/dashboard/client_detail.html` — yangi (profil + tablar)
- `templates/dashboard/wrapper.html` — sidebar havolalari yangilandi

**Test qilindi (lokal server, `user1`/`admin123` bilan kirib):**
login → `/usta/clients/2/` (Taminotchilar) ro'yxati ochildi → yangi mijoz
qo'shildi (POST) → ro'yxatda ko'rindi → profil sahifasi ochildi (to'g'ri
turi ko'rsatildi) → ma'lumotlar tahrirlandi (POST) → o'chirildi (soft-delete)
→ ro'yxatdan yo'qoldi. Barchasi kutilganidek ishladi, xatolik chiqmadi.

**Kelajakda e'tibor:** mijoz profilidagi "Pul tarixi" tabini Kassa
bosqichida, "Mahsulot tarixi" tabini Sotuv/Turnover bosqichida haqiqiy
ma'lumot bilan to'ldirish kerak. Profil sahifasida bo'lganda sidebar'da
tegishli menyu punkti "active" bo'lib ko'rinmaydi (kichik kosmetik nuqson,
muhim emas).

---

## 2026-07-17 — Admin panel sidebar tekshiruvi

**Nima qilindi:**
- Loyiha lokal ishga tushirildi (`manage.py runserver`), `/usta/login/`
  orqali `user1` bilan kirildi va `/usta/` sahifasi tekshirildi.
- `templates/dashboard/wrapper.html` ichidagi haqiqiy sidebar aniqlandi
  (`static/partials/_sidebar.html` — ishlatilmaydigan theme namunasi
  ekani aniqlandi, chalkashlikka sabab bo'lmasin uchun eslatib qo'yaman).

**Natija — sidebar tuzilishi (5 bo'lim):**
| Bo'lim | Punktlar | Holati |
|---|---|---|
| Asosiy | Bosh sahifa | ✅ ishlaydi |
| Ishchilar | Ishlar Ro'yxati, Ishchilar Ro'yxati, Pul berish, Jarimalar | ✅ ishlaydi |
| Mijozlar | Haridorlar, Taminotchilar, Turli shaxslar | ⚠️ placeholder (`/usta/`ga qaraydi) |
| Moliya | Kassa, Sotuv | ⚠️ placeholder (`/usta/`ga qaraydi) |
| Ombor | Mahsulotlar, Ombor | ✅ ishlaydi |
| Ombor | Mahsulot kirim, Mahsulot chiqim | ⚠️ placeholder (`/usta/`ga qaraydi) |

**Fayllar:** o'zgartirilmadi (faqat tekshiruv).

**Kelajakda e'tibor:** yuqoridagi ⚠️ belgilangan 5 ta menyu punkti uchun
hali view/URL yozilmagan — `dashboard/urls.py`, `dashboard/views.py` va
tegishli template'lar qo'shilishi kerak.
