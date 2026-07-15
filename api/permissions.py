from rest_framework.permissions import BasePermission

from main.tenancy import get_request_company


class IsActiveTenant(BasePermission):
    """Blocks any authenticated request whose tenant (Company) is
    suspended or whose subscription has expired."""

    def has_permission(self, request, view):
        company = get_request_company(request.user)
        return company is not None and company.has_access()
