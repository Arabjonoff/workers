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
from django.db.models import Q
from .sms_sender import sender_code, sender_gived_money

from datetime import datetime

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
            "cash": Cash.objects.filter(main=True),
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
            category = WorkCategory.objects.get(id=c_id)
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
        category = WorkCategory.objects.get(id=c_id)
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
            worker = WorkerProfile.objects.get(id=w_id)
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
    

def sms_send(request):
    
    admin_id = request.GET.get('id')
    admin = AdminProfile.objects.get(id=admin_id)
    
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

def check_day(request):
    day = request.GET.get('day')
    if day == 'all':
        days = Day.objects.filter(date__date=TODAY)

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
        pis = PIS.objects.filter(is_active=True).order_by('-id')
        storage = Storage.objects.filter(is_active=True)
        context = {
            'products': pis,
            'storages': storage,
            'types': get_product_types(),
            'mtypes': get_product_mtypes(),
        }
        return render(request, 'dashboard/products.html', context)

    def post(self, request):
        name = request.POST.get('name')
        type = request.POST.get('type')
        storage = request.POST.get('storage')
        mount = request.POST.get('mount')
        mtype = request.POST.get('mtype')
        try:
            product = Product.objects.create(
                name=name,
                type=type,
                m_type=mtype
            )
            PIS.objects.create(
                product=product,
                mount=mount,
                storage_id=storage,
                start_mount=mount
            )
            messages.success(request, 'Mahsulot qo`shildi.')
        except Exception as error:
            messages.error(request, f'Xatolik: {error}')
        
        return redirect(request.META['HTTP_REFERER'])
    
@login_required
def edit_pis(request, id):
    pis = PIS.objects.get(id=id)
    name = request.POST.get('name')
    type = request.POST.get('type')
    storage = request.POST.get('storage')
    mount = request.POST.get('mount')
    start_mount = request.POST.get('start_mount')
    mtype = request.POST.get('mtype')
    try:
        pis.product.name = name
        pis.product.type = type
        pis.product.m_type = mtype
        pis.storage = Storage.objects.get(id=storage)
        pis.mount = mount
        pis.start_mount = start_mount
        pis.product.save()
        pis.save()
        messages.success(request, 'Mahsulot saqlandi.')
    except Exception as error:
        messages.error(request, f'Xatolik: {error}')

    return redirect(request.META['HTTP_REFERER'])

@login_required
def delete_pis(request, id):
    pis = PIS.objects.get(id=id)
    pis.is_active = False
    pis.save()
    messages.success(request, 'Mahsulot o`chirildi')
    return redirect(request.META['HTTP_REFERER'])


@method_decorator(is_staff, name='dispatch')
class StoragesView(LoginRequiredMixin, View):
    def get(self, request):
        storages = Storage.objects.filter(is_active=True)
        return render(request, 'dashboard/storage.html')