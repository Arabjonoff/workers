from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from .decorators import is_staff
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from main.models import *
from main.funcs import *
from django.contrib import messages
from django.db.models import Q, Sum
from django.db import transaction
from .sms_sender import sender_code, sender_gived_money

from datetime import datetime
from decimal import Decimal, InvalidOperation

def get_product_types():
    data = []
    for i in PRODUCT_TYPES:
        dt = {
            'id': i[0],
            'name': i[1]
        }
        data.append(dt)
    return data

def get_product_mtypes():
    data = []
    for i in MTYPES:
        dt = {
            'id': i[0],
            'name': i[1]
        }
        data.append(dt)
    return data

@login_required
def search(request):
    query = request.GET.get('query')
    admin = request.user.admin
    workers = WorkerProfile.objects.filter(Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query), admin=admin)
    works = WorkCategory.objects.filter(Q(name__icontains=query) | Q(price__icontains=query), deleted=False, admin=admin)
    context = {
        'workers':workers,
        'works':works,
    }
    return render(request, 'dashboard/search.html', context)


class LoginView(LoginView):
    template_name = 'dashboard/login.html'


from django.utils.decorators import method_decorator

@method_decorator(is_staff, name='dispatch')
class HomePageView(LoginRequiredMixin, View):
    def get(self, request):
        admin = AdminProfile.objects.get(user=request.user)
        workers = WorkerProfile.objects.filter(admin=admin)
        categories = WorkCategory.objects.filter(admin=admin)
        bugs = BugWork.objects.filter(worker__admin=admin)
        balance = 0
        gave_balance = 0
        bugs_summa = 0
        for bug in bugs:
            bugs_summa += bug.price
        for history in BalanceHistory.objects.filter(deleted=False, worker__admin=admin):
            if 0 < history.got_sum:
                gave_balance += history.got_sum
        for worker in workers:
            if 0 < worker.balance:
                balance += worker.balance
            create_daily_works(worker.user)
        admin.workers_money = balance
        admin.gave_money = gave_balance
        admin.bugs_money = bugs_summa
        admin.save()

        # --- Grafiklar uchun ma'lumot ---
        from datetime import timedelta

        # 1) Ish hajmi trendi — ma'lumot mavjud bo'lgan so'nggi 14 kun (kunlik yig'indi)
        totals = {}
        for d in Day.objects.filter(worker__admin=admin):
            key = d.date.date()
            totals[key] = totals.get(key, 0) + (d.sum or 0)
        last_days = sorted(totals.keys())[-14:]
        trend_labels = [dd.strftime('%d.%m') for dd in last_days]
        trend_values = [totals[dd] for dd in last_days]

        # 2) Top ishchilar balansi (grafik uchun)
        top_workers = list(workers.order_by('-balance')[:7])
        worker_labels = [f"{w.user.first_name} {w.user.last_name}".strip() or w.user.username for w in top_workers]
        worker_values = [w.balance for w in top_workers]

        # 3) Eng qimmat ishlar (grafik uchun)
        top_cats = list(categories.filter(deleted=False).order_by('-price')[:7])
        cat_labels = [c.name for c in top_cats]
        cat_values = [c.price for c in top_cats]

        context = {
            "admin":admin,
            "workers_b":workers.order_by('-balance')[:5],
            "categories":categories.filter(deleted=False).order_by('-price')[:5],
            "cash": Cash.objects.filter(main=True, company=admin.company),
            # chart data
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "worker_labels": worker_labels,
            "worker_values": worker_values,
            "cat_labels": cat_labels,
            "cat_values": cat_values,
            "fin_gave": gave_balance,
            "fin_todo": balance,
            "fin_bugs": bugs_summa,
        }
        return render(request, 'dashboard/index.html', context)

    def post(self, request):
        try:
            name = request.POST.get('name')
            mount = request.POST.get('mount')
            currency = request.POST.get('currency')
            Cash.objects.create(
                company=request.user.admin.company,
                name=name,
                mount=mount,
                currency=currency,
                start_mount=mount,
                main=True
            )
            messages.success(request, 'Hamyon qo`shildi')
        except Exception as error:
            messages.error(request, f'{error}')
        return redirect('home')
    

@method_decorator(is_staff, name='dispatch')
class PlanWorksView(LoginRequiredMixin, View):
    def get(self, request):
        admin = AdminProfile.objects.get(user=request.user)
        context = {
            "admin":admin
        }
        return render(request, 'dashboard/planworks.html', context)


@method_decorator(is_staff, name='dispatch')
class AddWorkerView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/add_worker.html')

    def post(self, request):
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        birth = request.POST.get('birth')
        address = request.POST.get('address')
        balance = int(request.POST.get('balance'))
        homenumber = int(request.POST.get('homenumber')) if request.POST.get('homenumber') else None
        admin = AdminProfile.objects.get(user=request.user)
        status = create_workerprofile(
            admin_user=admin,
            phone=phone,
            f_name=first_name,
            l_name=last_name,
            birth=birth,
            address=address,
            balance=balance,
            home=homenumber,
            password=password
        )
        messages.info(request, status)

        return render(request, 'dashboard/add_worker.html')
    

@method_decorator(is_staff, name='dispatch')
class AddWorkView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/add_work.html')

    def post(self, request):
        try:
            work_name = request.POST.get('name')
            price = request.POST.get('price')
            type = request.POST.get('type')
            category = add_work(request.user, work_name, price, type)
            messages.success(request, 'Ish qo`shildi')
        except:
            messages.warning(request, 'Nimadur noto`g`ri ketdi')

        return render(request, 'dashboard/add_work.html')
    

@method_decorator(is_staff, name='dispatch')
class WorksListView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            c_id = int(request.GET.get("id"))
            category = get_object_or_404(WorkCategory, id=c_id, admin=request.user.admin)
            works = Work.objects.filter(category=category)
            for work in works:
                if work.sum == 0:
                    work.delete()
            category.deleted = True
            category.save()
            return redirect('/usta/works') 
        except:
            categories = WorkCategory.objects.filter(admin=request.user.admin, deleted=False)
            context = {
                'works':categories
            }
            return render(request, 'dashboard/works_list.html', context)

    def post(self, request):
        c_id = int(request.POST.get("id"))
        name = request.POST.get("name")
        price = request.POST.get("price")
        category = get_object_or_404(WorkCategory, id=c_id, admin=request.user.admin)
        category.name = name
        category.price = price
        category.save()
        return redirect('/usta/works')
    

@method_decorator(is_staff, name='dispatch')
class WorkersListView(LoginRequiredMixin, View):
    def get(self, request):
        workers = WorkerProfile.objects.filter(admin=request.user.admin)
        context = {
            'workers':workers
        }
        return render(request, 'dashboard/workers_list.html', context)


@method_decorator(is_staff, name='dispatch')
class WorkerProfileView(LoginRequiredMixin, View):
    def get(self, request, id):
        worker = get_object_or_404(WorkerProfile, id=id, admin=request.user.admin)
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        days = Day.objects.filter(worker=worker)
        if start_date and end_date:
            days = days.filter(date__date__gte=start_date, date__date__lte=end_date)
        else:
            days = days.filter(date__date__gte=datetime.now().date().replace(day=1))
        for day in days:
            works = Work.objects.filter(day=day)
            works_sum = 0
            for work in works:
                works_sum += work.sum
            day.worker.balance -= day.sum
            day.worker.balance += works_sum
            day.sum = works_sum
            day.save()
            day.worker.save()

        context = {
            'filter_date':{
                'start_date': start_date,
                'end_date': end_date
            },
            'worker':worker,
            'days':days
        }
        return render(request, 'dashboard/detail.html', context)

    def post(self, request, id):
        worker = get_object_or_404(WorkerProfile, id=id, admin=request.user.admin)
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        birth = request.POST.get('birth')
        address = request.POST.get('address')
        homenumber = request.POST.get('homenumber')
        password = request.POST.get('password')
        worker.user.first_name = first_name
        worker.user.last_name = last_name
        worker.user.username = phone
        worker.phone = phone
        worker.birth = birth
        worker.address = address
        worker.home_phone = homenumber if homenumber else None
        if password:
            worker.user.set_password(password)
        worker.save()
        worker.user.save()
        return redirect(f'/usta/worker/{worker.id}')
        
    

@method_decorator(is_staff, name='dispatch')
class GiveMoneyHistoryListView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            w_id = request.GET.get('worker_id')
            worker = get_object_or_404(WorkerProfile, id=w_id, admin=request.user.admin)
            if worker.balance > 0:
                balance = worker.balance
            else:
                balance = 0
            return JsonResponse({"balance":balance})
        except:
            workers = WorkerProfile.objects.filter(admin=request.user.admin)
            total_given = sum(w.got_balance for w in workers)
            recipients = sum(1 for w in workers if w.got_balance > 0)
            to_pay = sum(w.balance for w in workers if w.balance > 0)
            context = {
                'workers':workers,
                'total_given':total_given,
                'recipients':recipients,
                'to_pay':to_pay,
            }
            return render(request, 'dashboard/history.html', context)

    def post(self, request):
        w = int(request.POST.get('worker'))
        worker = WorkerProfile.objects.get(id=w, admin=request.user.admin)
        price = int(request.POST.get('price'))
        balance = BalanceHistory.objects.create(
            worker=worker,
            got_sum=price
        )
        worker.balance -= price
        worker.got_balance += price
        worker.save()
        text = f"Ismi: {worker.user.first_name}\nBerilgan summa: {price} so`m"
        sender_gived_money(str(worker.home_phone), text)
        return redirect('/usta/give_money')



@method_decorator(is_staff, name='dispatch')
class BugWorksView(LoginRequiredMixin, View):
    def get(self, request):
        bugs = WorkerProfile.objects.filter(admin=request.user.admin)
        total_bugs = sum(w.bugs_sum for w in bugs)
        fined = sum(1 for w in bugs if w.bugs.all().count() > 0)
        context = {
            'bugs':bugs,
            'total_bugs':total_bugs,
            'fined':fined,
        }
        return render(request, 'dashboard/bug-works.html', context)

    def post(self, request):
        admin = AdminProfile.objects.get(user=request.user)
        w = int(request.POST.get('worker'))
        worker = WorkerProfile.objects.get(id=w, admin=admin)
        price = int(request.POST.get('price'))
        info = str(request.POST.get('info'))
        BugWork.objects.create(
            worker=worker,
            price=price,
            info=info
        )
        worker.bugs_sum += price
        worker.save()
        admin.bugs_money +=price
        admin.save()
        return redirect('/usta/bugs')
    

@is_staff
def sms_send(request):

    admin = request.user.admin

    try:
        phone = str(request.GET.get('phone'))
    except:
        phone = 'none'
    sender = sender_code(phone)
    admin.code = sender['code']
    admin.save()
        
    return JsonResponse({"status":sender['status']})

@is_staff
def status_worker(request):
    wid = int(request.GET.get('id'))
    status = request.GET.get('status')
    worker = WorkerProfile.objects.get(id=wid, admin=request.user.admin)
    if status == 'true':
        worker.active = True
    elif status == 'false':
        worker.active = False
    worker.save()
    return JsonResponse({"ok":True})

@is_staff
def status_work(request):
    id = int(request.GET.get('id'))
    wid = int(request.GET.get('wid'))
    status = request.GET.get('status')
    worker = WorkerProfile.objects.get(id=wid, admin=request.user.admin)
    create_daily_works(worker.user)
    category = WorkCategory.objects.get(id=id, admin=request.user.admin)
    work = Work.objects.filter(day__worker=worker, category=category).last()
    if status == 'true':
        work.active = True
        worker.works.add(category)
        response = 'added work'

    elif status == 'false':
        work.active = False
        worker.works.remove(category)
        response = 'removed work'
    
    work.save()
    worker.save()
    return JsonResponse({"response":response})

@is_staff
def clear_history(request):
    admin = request.user.admin
    type = request.GET.get('type')
    if type == 'gave_money':
        worker_id = int(request.GET.get('worker'))
        worker = WorkerProfile.objects.get(id=worker_id, admin=admin)
        b_history = BalanceHistory.objects.filter(worker=worker)
        worker.got_balance = 0
        worker.save()
        for b in b_history:
            b.deleted = True
            b.save()
        return redirect('/usta/give_money')
    elif type == 'bug':
        worker_id = int(request.GET.get('worker'))
        worker = WorkerProfile.objects.get(id=worker_id, admin=admin)
        worker.bugs_sum = 0
        worker.save()
        bugs = BugWork.objects.filter(worker=worker).delete()
        return redirect('/usta/bugs')
    # delete worker
    elif type == 'delete_worker':
        worker_id = int(request.GET.get('worker'))
        worker = WorkerProfile.objects.get(id=worker_id, admin=admin)
        worker.user.delete()
        return redirect('/usta/workers')
    # delete all bug works
    elif type == 'bug_all':
        workers = WorkerProfile.objects.filter(admin=admin)
        for worker in workers:
            worker.bugs_sum = 0
            worker.save()
        BugWork.objects.filter(worker__admin=admin).delete()
        return redirect('/usta/bugs')
    # delete all balance history
    elif type == 'balance_all':
        workers = WorkerProfile.objects.filter(admin=admin)
        for worker in workers:
            worker.got_balance = 0
            worker.save()
        balance = BalanceHistory.objects.filter(worker__admin=admin)
        for b in balance:
            b.deleted = True
            b.save()
        return redirect('/usta/give_money')
    

@method_decorator(is_staff, name='dispatch')
class ProductsView(LoginRequiredMixin, View):
    def get(self, request):
        company = request.user.admin.company
        pis = PIS.objects.filter(is_active=True, company=company).order_by('-id')
        storage = Storage.objects.filter(is_active=True, company=company)
        context = {
            'products': pis,
            'storages': storage,
            'types': get_product_types(),
            'mtypes': get_product_mtypes(),
        }
        return render(request, 'dashboard/products.html', context)

    def post(self, request):
        company = request.user.admin.company
        name = request.POST.get('name')
        type = request.POST.get('type')
        storage = request.POST.get('storage')
        mount = request.POST.get('mount')
        mtype = request.POST.get('mtype')
        standard_price = request.POST.get('standard_price') or None
        try:
            storage_obj = get_object_or_404(Storage, id=storage, company=company)
            product = Product.objects.create(
                company=company,
                name=name,
                type=type,
                m_type=mtype,
                standard_price=standard_price
            )
            PIS.objects.create(
                company=company,
                product=product,
                mount=mount,
                storage=storage_obj,
                start_mount=mount
            )
            messages.success(request, 'Mahsulot qo`shildi.')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        
        return redirect(request.META['HTTP_REFERER'])
    
@is_staff
def edit_pis(request, id):
    company = request.user.admin.company
    pis = get_object_or_404(PIS, id=id, company=company)
    name = request.POST.get('name')
    type = request.POST.get('type')
    storage = request.POST.get('storage')
    mount = request.POST.get('mount')
    start_mount = request.POST.get('start_mount')
    mtype = request.POST.get('mtype')
    standard_price = request.POST.get('standard_price') or None
    try:
        pis.product.name = name
        pis.product.type = type
        pis.product.m_type = mtype
        pis.product.standard_price = standard_price
        pis.storage = get_object_or_404(Storage, id=storage, company=company)
        pis.mount = mount
        pis.start_mount = start_mount
        pis.product.save()
        pis.save()
        messages.success(request, 'Mahsulot saqlandi.')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')

    return redirect(request.META['HTTP_REFERER'])

@is_staff
def delete_pis(request, id):
    pis = get_object_or_404(PIS, id=id, company=request.user.admin.company)
    pis.is_active = False
    pis.save()
    messages.success(request, 'Mahsulot o`chirildi')
    return redirect(request.META['HTTP_REFERER'])


@method_decorator(is_staff, name='dispatch')
class StoragesView(LoginRequiredMixin, View):
    def get(self, request):
        storages = Storage.objects.filter(is_active=True, company=request.user.admin.company).order_by('name')
        context = {
            'storages': storages,
            'types': get_product_types(),
        }
        return render(request, 'dashboard/storage.html', context)

    def post(self, request):
        company = request.user.admin.company
        try:
            Storage.objects.create(
                company=company,
                name=request.POST.get('name'),
                type=request.POST.get('type'),
            )
            messages.success(request, 'Ombor qo`shildi')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        return redirect('/usta/storages/')


@is_staff
def edit_storage(request, id):
    storage = get_object_or_404(Storage, id=id, company=request.user.admin.company)
    try:
        storage.name = request.POST.get('name')
        storage.type = request.POST.get('type')
        storage.save()
        messages.success(request, 'Ombor saqlandi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('/usta/storages/')


@is_staff
def delete_storage(request, id):
    storage = get_object_or_404(Storage, id=id, company=request.user.admin.company)
    try:
        storage.is_active = False
        storage.save()
        messages.success(request, 'Ombor o`chirildi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('/usta/storages/')


CLIENT_TYPE_NAMES = {1: "Haridorlar", 2: "Taminotchilar", 3: "Turli shaxslar"}


@method_decorator(is_staff, name='dispatch')
class ClientsView(LoginRequiredMixin, View):
    def get(self, request, type):
        company = request.user.admin.company
        query = request.GET.get('query')
        clients = Client.objects.filter(company=company, type=type, is_active=True).order_by('-id')
        if query:
            clients = clients.filter(
                Q(name__icontains=query) | Q(phone1__icontains=query) | Q(phone2__icontains=query)
            )
        context = {
            'clients': clients,
            'type': type,
            'type_name': CLIENT_TYPE_NAMES.get(type, 'Mijozlar'),
            'query': query or '',
        }
        return render(request, 'dashboard/clients.html', context)

    def post(self, request, type):
        company = request.user.admin.company
        try:
            Client.objects.create(
                company=company,
                name=request.POST.get('name'),
                type=type,
                phone1=request.POST.get('phone1') or None,
                phone2=request.POST.get('phone2') or None,
                card_number=request.POST.get('card_number') or None,
                address=request.POST.get('address') or None,
            )
            messages.success(request, 'Mijoz qo`shildi')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        return redirect('clients', type=type)


@method_decorator(is_staff, name='dispatch')
class ClientProfileView(LoginRequiredMixin, View):
    def get(self, request, id):
        company = request.user.admin.company
        client = get_object_or_404(Client, id=id, company=company)
        payments = Payment.objects.filter(
            company=company, client_cash__client=client, is_active=True, type__in=[1, 2]
        ).order_by('-created')
        turnovers = _with_totals(
            Turnover.objects.for_company(company).filter(client=client).order_by('-created_date')
            .prefetch_related('products__product__product', 'products__product__storage')
        )
        context = {
            'client': client,
            'type_name': CLIENT_TYPE_NAMES.get(client.type, 'Mijoz'),
            'client_cashes': client.cashs.filter(is_active=True),
            'payments': payments,
            'turnovers': turnovers,
        }
        return render(request, 'dashboard/client_detail.html', context)

    def post(self, request, id):
        company = request.user.admin.company
        client = get_object_or_404(Client, id=id, company=company)
        try:
            client.name = request.POST.get('name')
            client.phone1 = request.POST.get('phone1') or None
            client.phone2 = request.POST.get('phone2') or None
            client.card_number = request.POST.get('card_number') or None
            client.address = request.POST.get('address') or None
            client.save()
            messages.success(request, 'Ma`lumotlar yangilandi')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        return redirect('client_detail', id=client.id)


@is_staff
def delete_client(request, id):
    client = get_object_or_404(Client, id=id, company=request.user.admin.company)
    client.is_active = False
    client.save()
    messages.success(request, 'Mijoz o`chirildi')
    return redirect('clients', type=client.type)


def _get_or_create_client_cash(company, client, currency):
    """Mijozning shu valyutadagi sub-hisobini topadi, bo'lmasa yaratadi.
    Mantiq api/views.py PaymentsViewSet.add bilan bir xil bo'lishi kerak."""
    client_cash = Cash.objects.filter(client=client, currency=currency, company=company).first()
    if not client_cash:
        client_cash = Cash.objects.create(company=company, client=client, currency=currency, name=f'{client.name}')
    return client_cash


def _parse_mount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError('Summa noto`g`ri kiritildi')


@method_decorator(is_staff, name='dispatch')
class KassaView(LoginRequiredMixin, View):
    def get(self, request):
        company = request.user.admin.company
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        payments = Payment.objects.filter(
            company=company, is_active=True, type__in=[1, 2, 3]
        ).order_by('-created')
        if start_date and end_date:
            payments = payments.filter(date__date__gte=start_date, date__date__lte=end_date)
        else:
            payments = payments.filter(date__date__gte=datetime.now().date().replace(day=1))
        context = {
            'cashes': Cash.objects.filter(company=company, main=True, is_active=True),
            'clients': Client.objects.filter(company=company, is_active=True).order_by('name'),
            'categories': OutcomeCategory.objects.filter(company=company, is_active=True),
            'payments': payments,
            'filter_date': {'start_date': start_date, 'end_date': end_date},
            'currencies': CURRENCY_TYPES,
        }
        return render(request, 'dashboard/kassa.html', context)


@is_staff
def add_cash(request):
    company = request.user.admin.company
    try:
        mount = _parse_mount(request.POST.get('mount') or 0)
        Cash.objects.create(
            company=company,
            name=request.POST.get('name'),
            currency=request.POST.get('currency'),
            mount=mount,
            start_mount=mount,
            main=True,
        )
        messages.success(request, 'Hamyon qo`shildi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('kassa')


@is_staff
def add_outcome_category(request):
    company = request.user.admin.company
    try:
        OutcomeCategory.objects.create(company=company, name=request.POST.get('name'))
        messages.success(request, 'Turkum qo`shildi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('kassa')


def _record_client_payment(company, cash, client, mount, direction, comment=None, date=None):
    """Haqiqiy pul harakati: cash va client_cash'ni yangilaydi, Payment yozadi.
    direction='in'  -> mijozdan pul keldi  (Kirim, type=1, kassa +, mijoz qarzi -)
    direction='out' -> mijozga pul berildi (Chiqim, type=2, kassa -, mijoz qarzi +)
    `cash_income`/`cash_outcome` va Turnover to'lovi (Sotuv/Olish) shu funksiyani ishlatadi,
    shunda ikkalasida ham bir xil hisob-kitob kafolatlanadi."""
    client_cash = _get_or_create_client_cash(company, client, cash.currency)
    client_before = client_cash.mount
    cash_before = cash.mount
    if direction == 'in':
        cash.mount += mount
        client_cash.mount -= mount
        p_type = 1
    else:
        cash.mount -= mount
        client_cash.mount += mount
        p_type = 2
    Payment.objects.create(
        company=company, cash=cash, client_cash=client_cash,
        mount=mount, date=date or datetime.now(),
        comment=comment or 'Izoh yo`q',
        currency=cash.currency, cash_before=cash_before, cash_after=cash.mount,
        client_before=client_before, client_after=client_cash.mount, type=p_type
    )
    cash.save()
    client_cash.save()
    return client_cash


@is_staff
def cash_income(request):
    """Kirim: mijozdan pul kelib tushdi -> kassa oshadi, mijoz qarzi kamayadi."""
    company = request.user.admin.company
    try:
        cash = get_object_or_404(Cash, id=request.POST.get('cash'), company=company)
        client = get_object_or_404(Client, id=request.POST.get('client'), company=company)
        mount = _parse_mount(request.POST.get('mount'))
        _record_client_payment(company, cash, client, mount, 'in', request.POST.get('comment'), request.POST.get('date'))
        messages.success(request, 'Kirim qilindi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('kassa')


@is_staff
def cash_outcome(request):
    """Chiqim: mijozga pul berildi -> kassa kamayadi, mijoz qarzi oshadi."""
    company = request.user.admin.company
    try:
        cash = get_object_or_404(Cash, id=request.POST.get('cash'), company=company)
        client = get_object_or_404(Client, id=request.POST.get('client'), company=company)
        mount = _parse_mount(request.POST.get('mount'))
        _record_client_payment(company, cash, client, mount, 'out', request.POST.get('comment'), request.POST.get('date'))
        messages.success(request, 'Chiqim qilindi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('kassa')


@is_staff
def cash_expense(request):
    """Harajat: kassadan xarajat uchun pul chiqdi -> mijozga aloqasi yo'q."""
    company = request.user.admin.company
    try:
        cash = get_object_or_404(Cash, id=request.POST.get('cash'), company=company)
        category_id = request.POST.get('category')
        category = get_object_or_404(OutcomeCategory, id=category_id, company=company) if category_id else None
        mount = _parse_mount(request.POST.get('mount'))

        cash_before = cash.mount
        cash.mount -= mount

        Payment.objects.create(
            company=company, cash=cash, mount=mount,
            date=request.POST.get('date') or datetime.now(),
            comment=request.POST.get('comment') or 'Izoh yo`q',
            currency=cash.currency, cash_before=cash_before, cash_after=cash.mount,
            type=3, category=category
        )
        cash.save()
        messages.success(request, 'Harajat qo`shildi')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('kassa')


TURNOVER_TYPE_NAMES = {1: 'Sotuv', 2: 'Mahsulot kirim'}


def _with_totals(turnovers):
    """Har bir Turnover'ga .total (ProductTurnover'lar yig'indisi) qo'shib beradi."""
    turnovers = list(turnovers)
    for t in turnovers:
        t.total = sum((pt.total_price for pt in t.products.all()), Decimal('0'))
    return turnovers


@method_decorator(is_staff, name='dispatch')
class TurnoverView(LoginRequiredMixin, View):
    def get(self, request, type):
        company = request.user.admin.company
        turnovers = _with_totals(
            Turnover.objects.for_company(company).filter(type=type).order_by('-created_date')
            .prefetch_related('products__product__product', 'products__product__storage')
        )
        pis_items = PIS.objects.filter(company=company, is_active=True).select_related('product', 'storage')
        if type == 1:
            pis_items = pis_items.filter(mount__gt=0)
        context = {
            'turnovers': turnovers,
            'type': type,
            'type_name': TURNOVER_TYPE_NAMES.get(type, 'Tranzaksiya'),
            'clients': Client.objects.filter(company=company, is_active=True).order_by('name'),
            'pis_items': pis_items,
            'cashes': Cash.objects.filter(company=company, main=True, is_active=True),
        }
        return render(request, 'dashboard/turnover.html', context)

    def post(self, request, type):
        company = request.user.admin.company
        try:
            client = get_object_or_404(Client, id=request.POST.get('client'), company=company)
            cash = get_object_or_404(Cash, id=request.POST.get('cash'), company=company)
            pis_ids = request.POST.getlist('product[]')
            mounts = request.POST.getlist('mount[]')
            prices = request.POST.getlist('price[]')
            bonus_prices = request.POST.getlist('bonus_price[]')
            bonus_mounts = request.POST.getlist('bonus_mount[]')

            if not pis_ids:
                raise ValueError('Kamida bitta mahsulot qo`shing')

            lines = []
            for i, pis_id in enumerate(pis_ids):
                if not pis_id:
                    continue
                pis = get_object_or_404(PIS, id=pis_id, company=company)
                mount = _parse_mount(mounts[i])
                price = _parse_mount(prices[i])
                bonus_price = _parse_mount(bonus_prices[i]) if i < len(bonus_prices) and bonus_prices[i] else Decimal('0')
                bonus_mount = _parse_mount(bonus_mounts[i]) if i < len(bonus_mounts) and bonus_mounts[i] else Decimal('0')
                total_mount = mount + bonus_mount
                if type == 1 and total_mount > pis.mount:
                    raise ValueError(f'"{pis.product.name}" omborda yetarli emas (mavjud: {pis.mount})')
                lines.append((pis, mount, price, bonus_price, bonus_mount))

            if not lines:
                raise ValueError('Kamida bitta mahsulot qo`shing')

            turnover = Turnover.objects.create(type=type, client=client, finished=True, finished_date=datetime.now())
            total_price = Decimal('0')
            for pis, mount, price, bonus_price, bonus_mount in lines:
                pt = ProductTurnover.objects.create(
                    product=pis, mount=mount, price=price,
                    bonus_price=bonus_price, bonus_mount=bonus_mount, status=2
                )
                turnover.products.add(pt)
                total_price += pt.total_price
                if type == 1:
                    pis.mount -= (mount + bonus_mount)
                else:
                    pis.mount += (mount + bonus_mount)
                pis.save()

            client_cash = _get_or_create_client_cash(company, client, cash.currency)
            if type == 1:
                client_cash.mount += total_price
            else:
                client_cash.mount -= total_price
            client_cash.save()

            if request.POST.get('paid_now') == 'on':
                paid_amount = _parse_mount(request.POST.get('paid_amount') or total_price)
                direction = 'in' if type == 1 else 'out'
                _record_client_payment(
                    company, cash, client, paid_amount, direction,
                    comment=f"{TURNOVER_TYPE_NAMES.get(type)} #{turnover.id} to`lovi",
                    date=request.POST.get('date')
                )

            messages.success(request, f'{TURNOVER_TYPE_NAMES.get(type)} saqlandi. Jami: {total_price}')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        return redirect('turnover', type=type)


def _material_price(material, company):
    """Hom-ashyo narxini aniqlaydi: standart narx bo'lsa undan, bo'lmasa
    oxirgi 'Olish' (Mahsulot kirim) tranzaksiyasidagi narxdan. Topilmasa None."""
    if material.standard_price is not None:
        return material.standard_price
    last = ProductTurnover.objects.filter(
        product__product=material, product__company=company, turnover__type=2
    ).order_by('-turnover__created_date', '-id').first()
    return last.price if last else None


def _material_stock(material, company):
    total = PIS.objects.filter(product=material, company=company, is_active=True).aggregate(s=Sum('mount'))['s']
    return total or Decimal('0')


def _recipe_cost(product, company):
    """1 dona tayyor mahsulot narxini hisoblaydi. Narxi nomalum hom-ashyolar bo'lsa,
    ularning nomi ro'yxatda qaytariladi (jami summaga qo'shilmaydi)."""
    items = RecipeItem.objects.filter(product=product).select_related('material')
    total = Decimal('0')
    missing = []
    for item in items:
        price = _material_price(item.material, company)
        if price is None:
            missing.append(item.material.name)
        else:
            total += price * item.mount
    return total, missing


def _recipe_stock_check(product, company, count):
    """Berilgan `count` dona tayyorlash uchun har bir hom-ashyo yetarlimi, va
    joriy zaxira bilan MAKSIMAL nechta dona tayyorlash mumkinligini hisoblaydi."""
    items = RecipeItem.objects.filter(product=product).select_related('material')
    rows = []
    max_producible = None
    for item in items:
        stock = _material_stock(item.material, company)
        needed = item.mount * count
        possible = int(stock // item.mount) if item.mount > 0 else 0
        max_producible = possible if max_producible is None else min(max_producible, possible)
        rows.append({
            'material': item.material,
            'per_unit': item.mount,
            'needed': needed,
            'stock': stock,
            'enough': stock >= needed,
            'shortage': max(needed - stock, Decimal('0')),
        })
    return rows, max_producible


@method_decorator(is_staff, name='dispatch')
class RecipeListView(LoginRequiredMixin, View):
    def get(self, request):
        company = request.user.admin.company
        products = Product.objects.filter(company=company).order_by('name')
        rows = []
        for p in products:
            items = RecipeItem.objects.filter(product=p)
            if items.exists():
                cost, missing = _recipe_cost(p, company)
                _, max_producible = _recipe_stock_check(p, company, Decimal('1'))
                rows.append({
                    'product': p, 'count': items.count(), 'cost': cost,
                    'missing': missing, 'max_producible': max_producible,
                })
        context = {'rows': rows, 'products': products}
        return render(request, 'dashboard/recipes.html', context)


@method_decorator(is_staff, name='dispatch')
class RecipeDetailView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        company = request.user.admin.company
        product = get_object_or_404(Product, id=product_id, company=company)
        items = RecipeItem.objects.filter(product=product).select_related('material')
        materials = Product.objects.filter(company=company).exclude(id=product.id).order_by('name')
        count_raw = request.GET.get('count')
        try:
            count = Decimal(str(count_raw)) if count_raw else Decimal('1')
        except InvalidOperation:
            count = Decimal('1')
        cost, missing_price = _recipe_cost(product, company)
        check_rows, max_producible = _recipe_stock_check(product, company, count)
        context = {
            'product': product,
            'items': items,
            'materials': materials,
            'storages': Storage.objects.filter(company=company, is_active=True).order_by('name'),
            'cost': cost,
            'missing_price': missing_price,
            'count': count,
            'check_rows': check_rows,
            'max_producible': max_producible,
        }
        return render(request, 'dashboard/recipe_detail.html', context)

    def post(self, request, product_id):
        company = request.user.admin.company
        product = get_object_or_404(Product, id=product_id, company=company)
        try:
            material_ids = request.POST.getlist('material[]')
            mounts = request.POST.getlist('mount[]')
            new_items = []
            seen = set()
            for i, mid in enumerate(material_ids):
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                material = get_object_or_404(Product, id=mid, company=company)
                mount = _parse_mount(mounts[i])
                if mount <= 0:
                    continue
                new_items.append((material, mount))
            if not new_items:
                raise ValueError('Kamida bitta hom-ashyo qo`shing')
            RecipeItem.objects.filter(product=product).delete()
            for material, mount in new_items:
                RecipeItem.objects.create(product=product, material=material, mount=mount)
            messages.success(request, 'Retsept saqlandi')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        return redirect('recipe_detail', product_id=product.id)


def _consume_material(material, company, needed):
    """Material zaxirasini turli omborlardagi PIS yozuvlaridan (eng ko'p
    zaxirali ombordan boshlab) ketma-ket kamaytiradi."""
    remaining = needed
    pis_entries = PIS.objects.filter(
        product=material, company=company, is_active=True, mount__gt=0
    ).order_by('-mount')
    for pis in pis_entries:
        if remaining <= 0:
            break
        take = min(pis.mount, remaining)
        pis.mount -= take
        pis.save()
        remaining -= take
    if remaining > 0:
        raise ValueError(f'"{material.name}" yetarli emas (yetishmayapti: {remaining})')


@is_staff
def produce_recipe(request, product_id):
    """Retsept asosida N dona tayyor mahsulot ishlab chiqaradi: xom-ashyoni
    omborlardan avtomatik kamaytiradi va tayyor mahsulotni tanlangan omborga qo'shadi."""
    company = request.user.admin.company
    product = get_object_or_404(Product, id=product_id, company=company)
    try:
        count_raw = request.POST.get('count')
        try:
            count = Decimal(str(count_raw)) if count_raw else None
        except InvalidOperation:
            count = None
        if not count or count <= 0:
            raise ValueError('Nechta dona ishlab chiqarilishini kiriting')

        storage = get_object_or_404(Storage, id=request.POST.get('storage'), company=company)

        items = list(RecipeItem.objects.filter(product=product).select_related('material'))
        if not items:
            raise ValueError('Avval retsept belgilang')

        check_rows, _ = _recipe_stock_check(product, company, count)
        not_enough = [r for r in check_rows if not r['enough']]
        if not_enough:
            details = ', '.join(f"{r['material'].name} (yetmaydi: {r['shortage']})" for r in not_enough)
            raise ValueError(f'Xom-ashyo yetarli emas: {details}')

        with transaction.atomic():
            for item in items:
                _consume_material(item.material, company, item.mount * count)
            pis, created = PIS.objects.get_or_create(
                product=product, storage=storage, company=company, is_active=True,
                defaults={'mount': 0, 'start_mount': 0}
            )
            pis.mount += count
            if created:
                pis.start_mount = count
            pis.save()

        messages.success(request, f'{count} dona "{product.name}" ishlab chiqarildi va "{storage.name}" omboriga qo`shildi.')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')
    return redirect('recipe_detail', product_id=product.id)