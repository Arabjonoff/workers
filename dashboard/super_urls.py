from django.urls import path
from . import super_views as v

urlpatterns = [
    path('', v.super_dashboard, name='super_dashboard'),
    path('login/', v.super_login, name='super_login'),
    path('logout/', v.super_logout, name='super_logout'),
    path('add/', v.add_company, name='super_add_company'),
    path('edit/<int:id>/', v.edit_company, name='super_edit_company'),
    path('toggle/<int:id>/', v.toggle_company, name='super_toggle_company'),
    path('renew/<int:id>/', v.renew_company, name='super_renew_company'),
]
