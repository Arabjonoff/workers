from django.shortcuts import redirect
from django.contrib.auth import logout
from functools import wraps

def is_staff(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user and request.user.is_staff:
            # Korxona admini (AdminProfile) bormi?
            try:
                admin = request.user.admin
            except Exception:
                admin = None
            if admin is None:
                # Superuser bo'lsa super panelga, aks holda login sahifasiga
                if request.user.is_superuser:
                    return redirect('/super/')
                logout(request)
                return redirect('/usta/login/')
            # Obuna bloklangan yoki muddati tugagan korxona kira olmaydi
            if not admin.company.has_access():
                logout(request)
                return redirect('/usta/login/?blocked=1')
            return view(request, *args, **kwargs)
        return redirect('/')
    return wrapper