from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("planworks/", PlanWorksView.as_view(), name="plan_works"),
    path("add_worker/", AddWorkerView.as_view(), name="add_worker"),
    path("add_work/", AddWorkView.as_view(), name="add_work"),
    path("works/", WorksListView.as_view(), name="works"),
    path("give_money/", GiveMoneyHistoryListView.as_view(), name="history"),
    path("bugs/", BugWorksView.as_view(), name="bugs"),
    path("workers/", WorkersListView.as_view(), name="workers"),
    path("products/", ProductsView.as_view(), name="products"),
    path("product_edit/<int:id>", edit_pis, name="product_edit"),
    path("product_delete/<int:id>", delete_pis, name="product_delete"),
    path("storages/", StoragesView.as_view(), name="storeges"),
    path("worker/<int:id>/", WorkerProfileView.as_view(), name="detail"),

    path("status_work/", status_work, name="status_work"),
    path("worker_status/", status_worker, name="status_worker"),
    path("send_sms/", sms_send, name="sms_send"),

    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("delete/", clear_history, name="delete"),
    path("search/", search, name="search"),
]
