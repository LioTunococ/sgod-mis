from django.core.management.base import BaseCommand

from organizations.models import School

# demo fixture data; in real use this could read from a file
SCHOOL_PROPS = {
    "floracentral": {"min_grade": 1, "max_grade": 6, "implements_adm": False},
    "sta-marcela-nhs": {"min_grade": 7, "max_grade": 12, "implements_adm": True},
    "calanasan-elem": {"min_grade": 1, "max_grade": 6, "implements_adm": False},
    "conner-nhs": {"min_grade": 7, "max_grade": 12, "implements_adm": True},
    "luna-es": {"min_grade": 1, "max_grade": 6, "implements_adm": False},
    "pudtol-nhs": {"min_grade": 7, "max_grade": 12, "implements_adm": True},
}


class Command(BaseCommand):
    help = "Seed demo school grade spans and ADM indicator"

    def handle(self, *args, **options):
        updated = 0
        for code, props in SCHOOL_PROPS.items():
            try:
                school = School.objects.get(code=code)
            except School.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"School not found: {code}"))
                continue
            for field, value in props.items():
                setattr(school, field, value)
            school.save(update_fields=list(props.keys()))
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} schools."))
