from django.contrib import admin
from .models import *

admin.site.register(AdminProfile)
admin.site.register(WorkerProfile)
admin.site.register(WorkCategory)
admin.site.register(Day)
admin.site.register(Work)
admin.site.register(Product)
admin.site.register(ProductCategory)
admin.site.register(ProductDesign)
admin.site.register(Storage)
admin.site.register(PIS)
admin.site.register(Cash)
admin.site.register(Client)
admin.site.register(Payment)
admin.site.register(Turnover)
admin.site.register(ProductTurnover)
admin.site.register(DateModel)
admin.site.register(SavolJavob)

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    fields = (('date',), 'info')
    readonly_fields = ('date',)
    search_fields = ('date',)