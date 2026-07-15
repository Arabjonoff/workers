
from django.contrib import admin
from django.urls import path, include
from . import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('super/', include('dashboard.super_urls')),
    path('usta/', include('dashboard.urls')),
    path('api/v1/', include('api.urls')),
    path('', include('main.urls')),
    path('api/rest/', include('rest_framework.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),
]

if settings.DEBUG == True:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)