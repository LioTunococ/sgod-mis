from django.core.management.base import BaseCommand
from django.db import models
from notifications.models import EmailNotification

class Command(BaseCommand):
    help = "Show notification counts and recent items (optionally filtered by recipient)."

    def add_arguments(self, parser):
        parser.add_argument("--to", dest="to", default=None, help="Filter by recipient email")
        parser.add_argument("--limit", type=int, default=10, help="Number of recent items to display")
        parser.add_argument("--show-errors", action="store_true", help="Show error_message for failed emails")

    def handle(self, *args, **opts):
        to = opts.get("to")
        limit = opts.get("limit")
        qs = EmailNotification.objects.all()
        if to:
            qs = qs.filter(to_email__iexact=to)
        counts = qs.values("status").order_by("status").annotate(c=models.Count("id"))
        self.stdout.write("Counts by status:")
        for row in counts:
            self.stdout.write(f"  {row['status']}: {row['c']}")
        self.stdout.write("")
        self.stdout.write("Recent notifications:")
        for n in qs.order_by("-id")[:limit]:
            line = f"[{n.id}] {n.status} to={n.to_email} retries={n.retry_count} subject={n.subject!r}"
            if n.status == EmailNotification.Status.FAILED and opts.get("show_errors"):
                line += f" error={n.error_message!r}"
            self.stdout.write(line)
