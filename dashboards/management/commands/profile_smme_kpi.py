from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
from django.conf import settings
import time


class Command(BaseCommand):
    help = "Profile SMME KPI API endpoints with common parameter combinations (DEBUG only)"

    def add_arguments(self, parser):
        parser.add_argument("--kpi-part", default="all", help="View to profile: all|implementation|slp|reading|rma|supervision")
        parser.add_argument("--reading-type", default="crla", help="crla|philiri when kpi-part=reading")
        parser.add_argument("--assessment-timing", default="bosy", help="bosy|mosy|eosy when kpi-part=reading")
        parser.add_argument("--page-size", type=int, default=50, help="Page size for pagination")
        parser.add_argument("--school-year", default=None, help="School year start, e.g., 2025")
        parser.add_argument("--quarter", default="all", help="Q1|Q2|Q3|Q4|all")
        parser.add_argument("--sort-by", default="school_name", help="Sort key for the view")
        parser.add_argument("--sort-dir", default="asc", help="asc|desc")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write(self.style.WARNING("DEBUG is False; profiling output may be limited. Set DEBUG=True for full query logging."))

        client = Client()
        # Authenticate as superuser if any exists; otherwise anonymous for public paths
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
        if user:
            client.force_login(user)

        url = reverse("smme_kpi_api")
        params = {
            "kpi_part": options["kpi_part"],
            "reading_type": options["reading_type"],
            "assessment_timing": options["assessment_timing"],
            "page": 1,
            "page_size": options["page_size"],
            "quarter": options["quarter"],
            "sort_by": options["sort_by"],
            "sort_dir": options["sort_dir"],
        }
        if options["school_year"]:
            params["school_year"] = options["school_year"]

        self.stdout.write(self.style.NOTICE(f"GET {url} with {params}"))
        t0 = time.time()
        resp = client.get(url, params)
        dt = time.time() - t0
        self.stdout.write(f"Status: {resp.status_code}; Time: {dt:.3f}s; Length: {len(resp.content)} bytes")
        if resp.status_code == 200:
            data = resp.json()
            self.stdout.write(f"View: {data.get('view')} | Total: {data.get('total')} | Page: {data.get('page')}/{(data.get('total') or 0 + data.get('page_size',1)-1) // max(data.get('page_size',1),1)}")
        else:
            self.stderr.write(self.style.ERROR(resp.content[:500]))

        self.stdout.write(self.style.SUCCESS("Done."))
