from .models import *
from datetime import datetime
from dateutil import rrule
import calendar
from  django.contrib.auth.models import User
import random
import requests
import json


def code_generator():
    ver_code_numbers = []
    for x in range(5):
        number = random.randint(1,9)
        ver_code_numbers.append(str(number))
    return "".join(ver_code_numbers)


def send_message_bot(message):
    TOKEN = '5963617228:AAFfFJ7BI_dg2vHuwtqpe1BgcL676VjVQeI'
    response = requests.post(
        url=f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        data={'chat_id': -1001890286740, 'text': message}
    ).json()
    if response:
        return response

TODAY = datetime.now().strftime('%Y-%m-%d')

def get_sum_for_worker(request_user):
    worker = WorkerProfile.objects.get(user=request_user)
    days = Day.objects.filter(worker=worker)
    summa = 0
    for day in days:
        summa += day.sum
    worker.balance = summa
    worker.save()
    return True

def filter_history(date, worker):
    date = date.split('-')
    year = date[0]
    month = date[1]
    f_date = Day.objects.filter(date__year=year, date__month=month, worker=worker)
    return f_date


def year_month_iter(user_id):
    worker = WorkerProfile.objects.get(user=user_id)
    start = worker.date.date()
    end = datetime.now().date()
    date_list = []
    for dt in rrule.rrule(rrule.MONTHLY, dtstart=start, until=end):
        date_list.append(dt.strftime('%Y-%m'))
    return date_list


def create_daily_works(request_user):
    worker = WorkerProfile.objects.get(user=request_user)
    day = Day.objects.filter(worker=worker).first()
    print('aaaaaaaaaaa')
    print(day)
    if not day:
        day = Day.objects.create(worker=worker)
        for n in worker.works.all():
            Work.objects.create(
                category=n,
                day=day
            )
    return day
    

def work_counter(work_id, count):
    work = Work.objects.get(id=work_id)
    work.sum = work.category.price * count
    if work.category.type == 'dona':
        work.count = int(count)
    else:
        work.length = count
    work.save()
    return True


def create_workerprofile(admin_user, phone, f_name, l_name, birth, address, balance, home, password=None):
    try:
        user = User.objects.create(
            username=phone,
            first_name=f_name,
            last_name=l_name
        )
        # Parolni admin belgilaydi; bo'sh bo'lsa zaxira variant
        if not password:
            password = f_name + phone[:-5]
        user.set_password(str(password))
        user.save()
        worker = WorkerProfile.objects.create(
            phone=phone,
            address=address,
            birth=birth,
            user=user,
            admin=admin_user,
            balance=balance,
            home_phone=home
        )
        for cat in WorkCategory.objects.filter(admin=admin_user):
            worker.works.add(cat)
        worker.save()
        status = 'Ishchi qo`shildi'
    except:
        status = 'Bu telefon raqam oldin qo`shilgan'

    return status

def add_work(request_user, work_name, price, type):
    admin = AdminProfile.objects.get(user=request_user)
    workers = WorkerProfile.objects.filter(admin=admin)
    category = WorkCategory.objects.create(
        admin=admin,
        name=work_name,
        price=price,
        type=type
    )
    for worker in workers:
        day = worker.days.first()
        Work.objects.create(
            day=day,
            category=category
        )
        worker.works.add(category)
        worker.save()
    return category