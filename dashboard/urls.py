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
    path("storage_edit/<int:id>", edit_storage, name="storage_edit"),
    path("storage_delete/<int:id>", delete_storage, name="storage_delete"),
    path("worker/<int:id>/", WorkerProfileView.as_view(), name="detail"),

    path("clients/<int:type>/", ClientsView.as_view(), name="clients"),
    path("client/<int:id>/", ClientProfileView.as_view(), name="client_detail"),
    path("client_delete/<int:id>", delete_client, name="client_delete"),

    path("kassa/", KassaView.as_view(), name="kassa"),
    path("kassa/add_cash/", add_cash, name="add_cash"),
    path("kassa/add_category/", add_outcome_category, name="add_outcome_category"),
    path("kassa/income/", cash_income, name="cash_income"),
    path("kassa/outcome/", cash_outcome, name="cash_outcome"),
    path("kassa/expense/", cash_expense, name="cash_expense"),

    path("turnover/<int:type>/", TurnoverView.as_view(), name="turnover"),

    path("recipes/", RecipeListView.as_view(), name="recipes"),
    path("recipe/<int:product_id>/", RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/<int:product_id>/produce/", produce_recipe, name="produce_recipe"),

    path("status_work/", status_work, name="status_work"),
    path("worker_status/", status_worker, name="status_worker"),
    path("send_sms/", sms_send, name="sms_send"),

    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("delete/", clear_history, name="delete"),
    path("search/", search, name="search"),
]
