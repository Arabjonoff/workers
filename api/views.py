from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from django.contrib.auth import authenticate
from main.models import *
from main.funcs import *
from .serializers import *
import json
from dashboard.sms_sender import sender_code, sender_gived_money

@api_view(['get'])
def base_data(request):
    gave_money = sum([i.mount for i in Payment.objects.filter(type=4)])
    balance = sum([i.balance for i in WorkerProfile.objects.filter(active=True)])
    bugs = sum([i.price for i in BugWork.objects.filter(worker__active=True)])
    return Response({
        'gave_money': gave_money,
        'balance': balance,
        'bugs': bugs,
    })

def get_date_model(request):
    date_model = DateModel.objects.last()
    if date_model:
        serializer = DateModelSerializer(date_model, many=False)
        return JsonResponse(serializer.data)
    else:
        return JsonResponse({'error': 'no date model'})


class WorkListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        day = create_daily_works(request.user)
        works = Work.objects.filter(day=day)
        worker = WorkerProfile.objects.get(user=request.user)
        works_sum = 0
        for work in works:
            works_sum += work.sum
        day.worker.balance -= day.sum
        day.worker.balance += works_sum
        day.sum = works_sum
        day.save()
        day.worker.save()
        work_serializer = WorksSerializer(works, many=True)
        day_serializer = DaysSerializer(day, many=False)
        worker_serializer = WorkerSerializer(worker, many=False)
        return Response({"worker":worker_serializer.data,"day":day_serializer.data,"works":work_serializer.data})
    
    def post(self, request):
        works = request.data['works']
        for work in works:
            work_obj = Work.objects.get(id=work['id'])
            work_obj.count = int(work['count'])
            work_obj.length = float(work['length'])
            work_obj.sum = work['sum']
            work_obj.save()
        return Response({"ok":True})


class HistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        worker = WorkerProfile.objects.get(user=request.user)
        try:
            filter = request.GET.get('filter')
            days = filter_history(filter, worker)
        except:
            days = Day.objects.filter(worker=worker)
            
        serializer = DaysSerializer(days, many=True)
        return Response(serializer.data)
    

class HistoryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        day = Day.objects.get(id=id)
        works = Work.objects.filter(day=day)
        works_serializer = WorksSerializer(works, many=True)
        day_serializer = DaysSerializer(day, many=False)
        return Response({"day":day_serializer.data,"works":works_serializer.data})
    

class LoginAPIView(APIView):
    def post(self, request):
        phone = request.data['phone']
        password = request.data['password']
        user = authenticate(request, username=phone, password=password)
        if user:
            worker = WorkerSerializer(user.worker)
            return Response({
                'success': True,
                'user': worker.data,
                'token': str(Token.objects.get(user=user).key)
            })
        else:
            return Response({
                'success': False,
                'error': "telefon yoki parol notog`ri."
            }, status=400)


class AdminLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            admin = AdminSerializer(user.admin)
            return Response({
                'user': admin.data,
                'token': str(Token.objects.get(user=user).key)
            })
        else:
            return Response({
                'error': "username yoki parol notog`ri."
            }, status=400)
    

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
        status = True
    else:
        status = False

    return JsonResponse({"ok":status})


from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_currency(request):
    data = []
    for i in CURRENCY_TYPES:
        cashs = Cash.objects.filter(currency=i[0])
        summa = sum([c.mount for c in cashs])
        dt = {
            'id': i[0],
            'name': i[1],
            'summa': summa
        }
        data.append(dt)
    return JsonResponse({'data': data})


class CashViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Cash.objects.filter(main=True, is_active=True)
    serializer_class = CashSerializer

    def create(self, request):
        try:
            name = request.data['name']
            currency = request.data['currency']
            mount = request.data['mount']
            Cash.objects.create(
                name=name,
                currency=currency,
                start_mount=mount,
                mount=mount,
                main=True
            )
            return Response({
                'success': True,
                'message': 'Qo`shildi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)


class WorkersViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = WorkerProfile.objects.filter(active=True)
    serializer_class = WorkerSerializer

    @action(methods=['get'], detail=False)
    def top5(self, request):
        workers = self.queryset.order_by('-balance')[:5]
        serializer = WorkerSerializer(workers, many=True)
        return Response(serializer.data)
    
    @action(methods=['post'], detail=False)
    def add(self, request):
        try:
            dt = request.data
            user = User.objects.create(
                username=str(dt['phone']),
                first_name=dt['first_name'],
                last_name=dt['last_name']
            )
            user.set_password(dt['password'])
            work = WorkerProfile.objects.create(
                user=user,
                admin=request.user.admin,
                birth=dt['birth'],
                address=dt['address'],
                phone=dt['phone']
            )
            work.works.set(dt['works'])
            work.save()
            user.save()
            return Response({
                'success': True,
                'message': 'Qo`shildi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    @action(methods=['post'], detail=False)
    def edit(self, request):
        try:
            dt = request.data
            worker = WorkerProfile.objects.filter(id=request.GET['id'])
            user = worker.last().user
            user.username=str(dt['phone'])
            user.first_name=dt['first_name']
            user.last_name=dt['last_name']
            worker.update(
                user=user,
                admin=request.user.admin,
                birth=dt['birth'],
                address=dt['address'],
                phone=dt['phone'],
                home_phone=dt['home_phone']
            )
            worker.last().works.set(dt['works'])
            worker.last().save()
            user.save()
            return Response({
                'success': True,
                'message': 'Yangilandi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
    
    @action(methods=['post'], detail=True)
    def reset_password(self, request, pk):
        try:
            worker = WorkerProfile.objects.get(id=pk)
            worker.user.set_password(request.data['password'])
            worker.user.save()
            return Response({
                'success': True,
                'message': 'Yangilandi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)

    @action(methods=['post'], detail=False)
    def pay(self, request):
        try:
            data = request.data
            # serializer = BalanceHistorySerializer(data=data)
            # if serializer.is_valid():
            #     cash = Cash.objects.get(id=data['cash'])
            #     cash.mount -= data['got_sum']
            #     serializer.save()
            #     cash.save()
            cash = Cash.objects.get(id=data['cash'])
            worker = WorkerProfile.objects.get(id=data['worker'])
            cash_before = cash.mount
            cash.mount -= data['mount']
            cash_after = cash.mount
            worker.balance -= data['mount']
            worker.got_balance += data['mount']
            Payment.objects.create(
                type=4,
                cash=cash,
                cash_before=cash_before,
                cash_after=cash_after,
                worker=worker,
                comment=data['comment'],
                mount=data['mount'],
                date=data['date']
            )
            worker.save()
            cash.save()
            text = f"Ismi: {worker.user.first_name}\nBerilgan summa: {data['mount']} so`m"
            sender_gived_money(str(worker.home_phone), text)
            return Response({
                'success': True,
                'message': 'To`lov qilindi'
            })
            # else:
            #     return Response({
            #         'success': False,
            #         'message': 'Malumotda xatolik bor',
            #         'error': serializer.errors
            #     }, status=400)
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)

    @action(methods=['get'], detail=True)
    def payments(self, request, pk):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            history = Payment.objects.filter(date__date__gte=start_date, date__date__lte=end_date, worker_id=pk)
            serializer = PaymentSerializer(history, many=True).data
            return Response(serializer)
        else:
            return Response([])
    
    @action(methods=['get'], detail=True)
    def works(self, request, pk):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            history = Day.objects.filter(date__date__gte=start_date, date__date__lte=end_date, worker_id=pk)
            serializer = DaysSerializer(history, many=True).data
            return Response(serializer)
        else:
            return Response([])
        
    @action(methods=['post'], detail=False)
    def edit_work(self, request):
        try:
            id = request.data['id']
            count = request.data.get('count', 0)
            work = Work.objects.get(id=id)
            work.day.worker.balance -= work.sum
            work.day.sum -= work.sum
            work.count = int(count)
            work.sum = work.category.price * work.count
            work.day.worker.balance += work.sum
            work.day.sum += work.sum
            work.save()
            work.day.save()
            work.day.worker.save()
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': WorksSerializer(work, many=False).data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        

class WorksViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = WorkCategory.objects.filter(deleted=False)
    serializer_class = CategoriesSerializer

    def create(self, request, *args, **kwargs):
        try:
            request.data['admin'] = request.user.admin.id
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)

    @action(methods=['get'], detail=False)
    def top5(self, request):
        works = self.queryset.order_by('-price')[:5]
        serializer = CategoriesSerializer(works, many=True)
        return Response(serializer.data)
    

class PISViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PIS.objects.filter(is_active=True)
    serializer_class = PISSerializer

    @action(methods=['post'], detail=False)
    def add(self, request):
        try:
            data = request.data
            product = Product.objects.create(
                name=data['name'],
                type=data['type'],
                category_id=data['category'],
                design_id=data['design'],
                m_type=data['m_type']
            )
            PIS.objects.create(
                product=product,
                mount=data['mount'],
                start_mount=data['mount'],
                storage_id=data['storage']
            )
            return Response({
                'success': True,
                'message': "Qo`shildi"
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    @action(methods=['post'], detail=False)
    def edit(self, request):
        try:
            id = request.GET.get('id')
            data = request.data
            pis = PIS.objects.filter(id=id)
            pis.update(
                storage_id=data['storage'],
                mount=data['mount']
            )
            product = Product.objects.filter(id=pis.last().product.id)
            product.update(
                name=data['name'],
                type=data['type'],
                m_type=data['m_type'],
                category_id=data['category'],
                design_id=data['design']
            )
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': PISSerializer(pis.last(), many=False).data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)


class ProductDesignViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ProductDesign.objects.filter(is_active=True)
    serializer_class = DesignSerializer


    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)


class StorageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Storage.objects.filter(is_active=True)
    serializer_class = StorageSerializer


    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)


class PaymentsViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.filter(is_active=True, type__in=[1, 2, 3])
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def list(self, *args, **kwargs):
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            self.queryset = self.queryset.filter(date__date__gte=start_date, date__date__lte=end_date)
        else:
            self.queryset = self.queryset.filter(date__date__gte=datetime.now().date().replace(day=1))
        return super().list(*args, **kwargs)
        
    def partial_update(self, request, pk, *args, **kwargs):
        try:
            payment = Payment.objects.get(pk=pk)
            edited_mount = request.data['mount'] - payment.mount
            if payment.type == 1:
                if not payment.for_product:
                    payment.cash.mount += edited_mount
                if payment.client_cash:
                    payment.client_cash.mount -= edited_mount
                payment.client_after = payment.client_cash.mount
            elif payment.type == 2:
                if not payment.for_product:
                    payment.cash.mount -= edited_mount
                if payment.client_cash:
                    payment.client_cash.mount += edited_mount
                payment.client_after = payment.client_cash.mount
            elif payment.type == 3:
                payment.cash.mount -= edited_mount
            else:
                payment.cash.mount -= edited_mount
                payment.worker.balance -= edited_mount
                payment.worker.got_balance += edited_mount
            payment.cash_after = payment.cash.mount
            response = super().partial_update(request, *args, **kwargs)
            payment.cash.save()
            payment.save()
            if payment.client_cash:
                payment.client_cash.save()
            if payment.worker:
                payment.worker.save()
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
    
    @action(methods=['post'], detail=False)
    def add(self, request):
        try:
            data = request.data
            product = data['product']
            cash = Cash.objects.get(id=data['cash'])
            client = Client.objects.get(id=data['client'])
            client_cash = Cash.objects.filter(client=client, currency=cash.currency).first()
            if not client_cash:
                client_cash = Cash.objects.create(client=client, currency=cash.currency, name=f'{client.name}')
            client_before = client_cash.mount
            cash_before = cash.mount
            if data['type'] == 1:
                if not product:
                    cash.mount += data['mount']
                client_cash.mount -= data['mount']
            elif data['type'] == 2:
                if not product:
                    cash.mount -= data['mount']
                client_cash.mount += data['mount']
            else:
                return Response({
                    'success': False,
                    'message': 'Turi kirim yoki chiqim bo`lishi kerak'
                }, status=400)
            client_after = client_cash.mount
            cash_after = cash.mount
            Payment.objects.create(
                cash=cash,
                for_product=product,
                client_cash=client_cash,
                mount=data['mount'],
                date=data['date'],
                comment=data['comment'],
                currency=cash.currency,
                cash_before=cash_before,
                cash_after=cash_after,
                client_before=client_before,
                client_after=client_after,
                type=data['type']
            )
            cash.save()
            client_cash.save()
            return Response({
                'success': True,
                'message': 'Qo`shildi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)

    @action(methods=['get'], detail=False)
    def worker_payments(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        balance = Payment.objects.filter(is_active=True, type=4)
        if start_date and end_date:
            balance = balance.filter(date__date__gte=start_date, date__date__lte=end_date)
        else:
            balance = balance.filter(date__date__gte=datetime.now().date().replace(day=1))
        serializer = PaymentSerializer(balance, many=True)
        return Response(serializer.data)
    
    @action(methods=['post'], detail=False)
    def outcome(self, request):
        try:
            data = request.data
            cash = Cash.objects.get(id=data['cash'])
            cash_before = cash.mount
            cash.mount -= data['mount']
            cash_after = cash.mount
            Payment.objects.create(
                cash=cash,
                mount=data['mount'],
                date=data['date'],
                comment=data['comment'],
                currency=cash.currency,
                cash_before=cash_before,
                cash_after=cash_after,
                type=3,
                category_id=data['category']
            )
            cash.save()
            return Response({
                'success': True,
                'message': 'Qo`shildi'
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
    

class ClientsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Client.objects.filter(is_active=True)
    serializer_class = ClientSerializer

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        

class OutcomeCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = OutcomeCategory.objects.filter(is_active=True)
    serializer_class = OutcomeCategorySerializer

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Qo`shildi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        
    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Yangilandi',
                'data': response.data
            })
        except Exception as err:
            return Response({
                'success': False,
                'message': 'Malumotda xatolik bor',
                'error': f"{err}"
            }, status=400)
        