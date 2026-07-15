from main.tenancy import get_request_company


class TenantScopedViewSetMixin:
    """Scopes list/retrieve/update/destroy to the requester's tenant and
    stamps the owning FK automatically on create.

    `tenant_lookup` is the ORM path from this model to its Company, e.g.
    'company' for models with a direct FK, or 'admin__company' for
    WorkerProfile/WorkCategory (which are owned via AdminProfile).
    """
    tenant_lookup = 'company'

    def get_queryset(self):
        qs = super().get_queryset()
        company = get_request_company(self.request.user)
        if company is None:
            return qs.none()
        return qs.filter(**{self.tenant_lookup: company})

    def perform_create(self, serializer):
        owner_field = self.tenant_lookup.split('__')[0]
        if owner_field == 'company':
            value = get_request_company(self.request.user)
        else:
            value = getattr(self.request.user, owner_field, None)
        serializer.save(**{owner_field: value})
