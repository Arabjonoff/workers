from datetime import date

from .models import WorkerProfile, Day, Work, Company, Backup

def create_day():
    for i in WorkerProfile.objects.filter(active=True).distinct():
        day = Day.objects.create(worker=i)
        for n in i.works.all():
            Work.objects.create(
                category=n,
                day=day
            )


def check_subscriptions():
    """Obuna muddati o'tgan korxonalarni avtomatik bloklaydi."""
    expired = Company.objects.filter(is_active=True, end_date__isnull=False, end_date__lt=date.today())
    count = expired.count()
    expired.update(is_active=False)
    if count:
        Backup.objects.create(info=f"{count} ta korxona obunasi tugagani uchun avtomatik bloklandi ({date.today()})")
    return count