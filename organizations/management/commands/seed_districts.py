from django.core.management.base import BaseCommand

from organizations.models import District

DISTRICTS = [
    ("flora", "Flora"),
    ("sta-marcela", "Sta. Marcela"),
    ("luna", "Luna"),
    ("pudtol", "Pudtol"),
    ("kabugao-1", "Kabugao 1"),
    ("kabugao-2", "Kabugao 2"),
    ("northern-conner", "Northern Conner"),
    ("southern-conner", "Southern Conner"),
    ("upper-calanasan", "Upper Calanasan"),
    ("lower-calanasan", "Lower Calanasan"),
]


class Command(BaseCommand):
    help = "Seed the fixed list of school districts"

    def handle(self, *args, **options):
        created = 0
        for code, name in DISTRICTS:
            _, was_created = District.objects.update_or_create(code=code, defaults={"name": name})
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded districts (created {created}, total {District.objects.count()})"))
