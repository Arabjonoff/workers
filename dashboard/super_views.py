from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from functools import wraps
from main.models import Company, AdminProfile, WorkerProfile, PLAN_TYPES


def super_required(view):
    """Faqat platforma egasi (Django superuser) kira oladi."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('/super/login/')
        return view(request, *args, **kwargs)
    return wrapper


def super_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('/super/')
    error = False
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('/super/')
        error = True
    return render(request, 'super/login.html', {'error': error})


def super_logout(request):
    logout(request)
    return redirect('/super/login/')


@super_required
def super_dashboard(request):
    companies = Company.objects.all()
    data = []
    for c in companies:
        admin = c.admins.first()
        data.append({
            'company': c,
            'admin': admin,
            'workers': WorkerProfile.objects.filter(admin__company=c).count() if admin else 0,
            'days_remaining': c.days_remaining,
            'is_expired': c.is_expired,
        })
    context = {
        'data': data,
        'total_companies': companies.count(),
        'active_companies': companies.filter(is_active=True).count(),
        'plan_types': PLAN_TYPES,
    }
    return render(request, 'super/index.html', context)


@super_required
def add_company(request):
    if request.method != 'POST':
        return redirect('/super/')
    name = request.POST.get('name')
    phone = request.POST.get('phone')
    username = request.POST.get('username')
    password = request.POST.get('password')
    first_name = request.POST.get('first_name')
    plan = request.POST.get('plan') or 'trial'
    price = request.POST.get('price') or 0
    duration_days = request.POST.get('duration_days')
    if User.objects.filter(username=username).exists():
        messages.error(request, 'Bu login band. Boshqa login tanlang.')
        return redirect('/super/')
    end_date = date.today() + timedelta(days=int(duration_days)) if duration_days else None
    company = Company.objects.create(
        name=name, phone=phone, plan=plan, price=price,
        start_date=date.today(), end_date=end_date,
    )
    user = User.objects.create(username=username, first_name=first_name or name, is_staff=True)
    user.set_password(password)
    user.save()
    AdminProfile.objects.create(user=user, company=company)
    messages.success(request, f"'{name}' korxonasi qo'shildi. Login: {username}")
    return redirect('/super/')


@super_required
def edit_company(request, id):
    if request.method != 'POST':
        return redirect('/super/')
    try:
        c = Company.objects.get(id=id)
    except Company.DoesNotExist:
        messages.error(request, 'Korxona topilmadi.')
        return redirect('/super/')
    admin = c.admins.first()
    name = request.POST.get('name')
    username = request.POST.get('username')
    password = request.POST.get('password')
    plan = request.POST.get('plan')
    price = request.POST.get('price')
    end_date = request.POST.get('end_date')
    if name:
        c.name = name
    if plan:
        c.plan = plan
    if price:
        c.price = price
    if end_date:
        c.end_date = end_date
    c.save()
    if admin and username:
        if User.objects.filter(username=username).exclude(id=admin.user_id).exists():
            messages.error(request, 'Bu login band. Boshqa login tanlang.')
            return redirect('/super/')
        admin.user.username = username
        if password:
            admin.user.set_password(password)
        admin.user.save()
    messages.success(request, f"'{c.name}' ma'lumotlari yangilandi.")
    return redirect('/super/')


@super_required
def toggle_company(request, id):
    try:
        c = Company.objects.get(id=id)
        c.is_active = not c.is_active
        c.save()
        messages.success(request, f"'{c.name}' holati o'zgartirildi.")
    except Company.DoesNotExist:
        messages.error(request, 'Korxona topilmadi.')
    return redirect('/super/')


@super_required
def renew_company(request, id):
    if request.method != 'POST':
        return redirect('/super/')
    try:
        c = Company.objects.get(id=id)
    except Company.DoesNotExist:
        messages.error(request, 'Korxona topilmadi.')
        return redirect('/super/')
    days = request.POST.get('days')
    end_date = request.POST.get('end_date')
    base = c.end_date if (c.end_date and c.end_date > date.today()) else date.today()
    if days:
        c.end_date = base + timedelta(days=int(days))
    elif end_date:
        c.end_date = end_date
    c.is_active = True
    c.save()
    messages.success(request, f"'{c.name}' obunasi uzaytirildi. Yangi tugash sanasi: {c.end_date}")
    return redirect('/super/')
