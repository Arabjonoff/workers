from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.http import JsonResponse
import json
import requests

from .models import *
from .funcs import *
from .decorators import *

from datetime import datetime


class ListView(LoginRequiredMixin, View):
    @is_worker
    def get(self, request):
        day = create_daily_works(request.user)
        worker = request.user.worker
        if day.date.date() == datetime.now().date():
            works = Work.objects.filter(day=day, active=True).order_by('-id')
            works_sum = 0
            for work in works:
                works_sum += work.sum
            day.worker.balance -= day.sum
            day.worker.balance += works_sum
            day.sum = works_sum
            day.save()
            day.worker.save()
            context = {
                'works':works,
                'day':day
                }
        else:
            day = Day.objects.create(worker=worker)
            for n in worker.works.all():
                Work.objects.create(
                    category=n,
                    day=day
                )
            works = Work.objects.filter(day=day)
            context = {
                'works': works,
                'day': day
            }
        return render(request, 'list.html', context)


class WorksView(LoginRequiredMixin, View):
    @is_worker
    def get(self, request):
        return render(request, 'works.html')


class HistoryView(LoginRequiredMixin, View):
    @is_worker
    def get(self, request):
        worker = WorkerProfile.objects.get(user=request.user)
        try:
            filter = request.GET.get('filter')
            days = filter_history(filter, worker)
        except:
            days = Day.objects.filter(worker=worker)
        ls = year_month_iter(request.user.id)
        context = {
            'months':ls,
            'days':days.order_by('-id')
        }
        return render(request, 'history.html', context)


class ProfileView(LoginRequiredMixin, View):
    @is_worker
    def get(self, request):
        worker = WorkerProfile.objects.get(user=request.user)
        context = {
            "worker":worker
        }
        return render(request, 'profil.html', context)
    

class LoginView(View):
    @is_worker
    def get(self, request):
        return render(request, 'login.html', {'error': False})

    @is_worker
    def post(self, request):
        # Telefon raqami = login (username), parolni admin belgilaydi
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=phone, password=password)
        # Faqat ishchilar (admin/staff bu yerdan kira olmaydi)
        if user is not None and not user.is_staff:
            login(request, user)
            return redirect('/')
        return render(request, 'login.html', {'error': True})



def worker_logout(request):
    auth_logout(request)
    return redirect('/login/')


def list_work_counter(request, id):
    value = request.GET.get('value')
    work = work_counter(id, float(value))
    return JsonResponse({'status':work})


def sms_send(request):
    
    USER_ID = '1257603816'
    MERCHANT_ID = 212
    TOKEN = 'THpraofsxAqQnkjOPEFSdmeLvRKNluhtbBZXVyIUGiDJYMg'
    CODE = code_generator()
    TEXT = f"Tasdiqlash kodi: {CODE}"
    
    try:
        phone = str(request.GET.get('phone'))
    except:
        phone = 'none'
    if phone.__len__() == 9:
        send_message_bot(TEXT+f"\nTelfon: {phone}")
        payload = json.dumps({
            "send": "",
            "text": TEXT,
            "number": phone,
            "user_id": USER_ID,
            "token": TOKEN,
            "id": MERCHANT_ID
        })
        worker = WorkerProfile.objects.get(phone=phone)
        url = "https://api.xssh.uz/smsv1/?data="+payload
        # response = requests.request("POST", url)
        worker.code = CODE
        worker.save()
        status = 'Xabar yuborildi'
    else:
        status = 'Xabar yuborilmadi'

    return JsonResponse({"status":status})


def qa_view(request):
    q = request.GET.get('q')
    q_obj = SavolJavob.objects.filter()
    if q_obj:
        q_obj = q_obj.filter(q__icontains=q)
    context = {
        'q': q_obj
    }
    return render(request, 'qa.html', context)

# works = [i.id for i in WorkCategory.objects.filter(deleted=False, admin_id=1).distinct()]

# for i in WorkerProfile.objects.all():
#     i.works.set(works)
#     print(i.works.all().values())