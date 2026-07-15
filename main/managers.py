from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(**{self.model.TENANT_LOOKUP: company})


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    pass
