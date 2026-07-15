from django.urls import path
from . import views

urlpatterns = [
    path("", views.ListView.as_view(), name="list"),
    path("works/", views.WorksView.as_view(), name="works"),
    path("history/", views.HistoryView.as_view(), name="history"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.worker_logout, name="worker_logout"),
    # for ajax
    path("ajax_work_counter/<int:id>", views.list_work_counter, name="ajax_work_count"),
    path("send_sms/", views.sms_send, name="sms_send"),
    path("qa/", views.qa_view, name="qa"),
]
