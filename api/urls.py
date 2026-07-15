from django.urls import path
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("today/", WorkListAPIView.as_view(), name="today"),
    path("send_code/", sms_send, name="sms_send"),
    path("get_currency/", get_currency, name="get_currency"),
    path("history_days/", HistoryAPIView.as_view(), name="history"),
    path("history_days/<int:id>", HistoryDetailAPIView.as_view(), name="history_detail"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("get_date_model/", get_date_model, name="get_date_model"),
    path("base_data/", base_data, name="base_data"),
    path("admin/login/", AdminLoginView.as_view(), name="login_admin"),
]

router.register('cashs', CashViewSet)
router.register('workers', WorkersViewSet)
router.register('works', WorksViewSet)
router.register('products', PISViewSet)
router.register('product_category', ProductCategoryViewSet)
router.register('product_design', ProductDesignViewSet)
router.register('storage', StorageViewSet)
router.register('payments', PaymentsViewSet)
router.register('clients', ClientsViewSet)
router.register('outcome', OutcomeCategoryViewSet)

urlpatterns += router.urls