from django.shortcuts import redirect

def is_worker(view):
    def wrapper(self,request,*args,**kwargs):
        if request.user.is_staff == False:
            return view(self, request, *args, **kwargs)
        return redirect('/usta')
    return wrapper