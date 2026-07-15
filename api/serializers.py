from rest_framework import serializers
from main.models import *
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['first_name','last_name','last_login']


class WorkerSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)
    class Meta:
        model = WorkerProfile
        fields = ['id', 'user', 'birth', 'address', 'balance', 'got_balance', 'bugs_sum', 'phone', 'home_phone', 'active', 'image', 'works']

class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)
    class Meta:
        model = AdminProfile
        fields = ['id', 'user', 'gave_money', 'workers_money', 'bugs_money']


class CategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'type', 'price', 'admin', 'deleted']
        read_only_fields = ['admin']


class WorksSerializer(serializers.ModelSerializer):
    category = CategoriesSerializer(many=False)
    class Meta:
        model = Work
        fields = ['id', 'category', 'count', 'length', 'sum', 'active']


class DaysSerializer(serializers.ModelSerializer):
    works = serializers.SerializerMethodField(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    theworks = WorksSerializer(many=True, read_only=True)
    class Meta:
        model = Day
        fields = ['id', 'worker', 'date', 'sum', 'works', 'theworks']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Filter the 'theworks' field based on a condition
        filtered_theworks = [work for work in representation['theworks'] if work.get('count') or work.get('length') > 0]

        representation['theworks'] = filtered_theworks

        return representation
    
    def get_works(self, instance):
        count = instance.theworks.filter(count__lt=0, active=True).count()
        return count
    
    def get_date(self, obj):
        return obj.date.date()


class ClientSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        # Customize how the data is represented
        representation = super().to_representation(instance)
        if instance.type == 1:
            type_display = 'Haridor'
        elif instance.type == 2:
            type_display = 'Taminotchi'
        else:
            type_display = 'Turli shaxs'
        representation['type_display'] = type_display
        
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ['company']

    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.client = datetime.now()
            date.save()
        return super().save(*args, **kwargs)

        
class CashSerializer(serializers.ModelSerializer):
    client = ClientSerializer(many=False)
    class Meta:
        model = Cash
        fields = [
            'id', 'name', 'get_currency_display', 'mount', 'start_mount', 'created', 'currency', 'client'
        ]
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.cash = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class ProductCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ['company']

    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.product_category = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class StorageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Storage
        fields = ['id', 'name', 'get_type_display', 'type']

    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.storage = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class DesignSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductDesign
        fields = ['id', 'name', 'is_active']
    
    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.product_design = datetime.now()
            date.save()
        return super().save(*args, **kwargs)


class ProductSerializer(serializers.ModelSerializer):
    design = DesignSerializer(many=False, read_only=True)
    category = ProductCategorySerializer(many=False, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'type', 'm_type', 'get_type_display', 'get_m_type_display', 'category', 'design']


class PISSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=False, read_only=True)
    storage = StorageSerializer(many=False, read_only=True)

    class Meta:
        model = PIS
        fields = '__all__'
        read_only_fields = ['company']


class DateModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = DateModel
        fields = '__all__'


class BalanceHistorySerializer(serializers.ModelSerializer):
    worker = WorkerSerializer(many=False)
    cash = CashSerializer(many=False)
    class Meta:
        model = BalanceHistory
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    # worker = WorkerSerializer(many=False)
    # client_cash = CashSerializer(many=False)
    cash = CashSerializer(many=False)
    def to_representation(self, instance):
        # Customize how the data is represented
        representation = super().to_representation(instance)
        representation['worker'] = {
            "first_name": instance.worker.user.first_name,
            "last_name": instance.worker.user.last_name
        } if instance.worker else None

        representation['client'] = {
            "name": instance.client_cash.client.name,
            "phone": instance.client_cash.client.phone1
        } if instance.client_cash else None

        representation['category'] = {
            "id": instance.category.id,
            "name": instance.category.name
        } if instance.category else None

        return representation
    class Meta:
        model = Payment
        fields = ['id', 'date', 'mount', 'currency', 'get_type_display', 'comment', 'worker', 'client_cash', 'client_before', 'client_after', 'cash', 'cash_before', 'cash_after', 'for_product', 'created']


class OutcomeCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = OutcomeCategory
        fields = '__all__'
        read_only_fields = ['company']

    def save(self, *args, **kwargs):
        date = DateModel.objects.last()
        if date:
            date.outcome_category = datetime.now()
            date.save()
        return super().save(*args, **kwargs)