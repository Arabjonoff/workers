from django.shortcuts import redirect
from django.contrib.auth import logout

from main.tenancy import get_request_company


class TenantAccessMiddleware:
    """Safety net: blocks suspended/expired-subscription tenants even on
    views that forget to apply the @is_staff / @is_worker decorator.
    DRF's IsActiveTenant permission covers /api/, so this only needs to
    watch the dashboard + worker-portal paths."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/') and request.user.is_authenticated:
            company = get_request_company(request.user)
            if company is not None and not company.has_access():
                is_staff = request.user.is_staff
                logout(request)
                target = '/usta/login/?blocked=1' if is_staff else '/login/?blocked=1'
                return redirect(target)
        return self.get_response(request)
