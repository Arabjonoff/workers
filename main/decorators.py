from django.shortcuts import redirect
from django.contrib.auth import logout

from .tenancy import get_request_company

def is_worker(view):
    def wrapper(self,request,*args,**kwargs):
        if request.user.is_staff == False:
            company = get_request_company(request.user)
            if company is not None and not company.has_access():
                logout(request)
                return redirect('/login/?blocked=1')
            return view(self, request, *args, **kwargs)
        return redirect('/usta')
    return wrapper