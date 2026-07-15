from .models import WorkerProfile, Day, Work

def create_day():
    for i in WorkerProfile.objects.filter(active=True).distinct():
        day = Day.objects.create(worker=i)
        for n in i.works.all():
            Work.objects.create(
                category=n,
                day=day
            )