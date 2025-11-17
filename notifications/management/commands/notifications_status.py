from django.core.management.base import BaseCommand
from notifications.models import EmailNotification

class Command(BaseCommand):
    help = "Show notification counts and recent items (optionally filtered by recipient)."

    def add_arguments(self, parser):
        parser.add_argument("--to", dest="to", default=None, help="Filter by recipient email")
        parser.add_argument("--limit", type=int, default=10, help="Number of recent items to display")

    def handle(self, *args, **opts):
        to = opts.get("to")
        limit = opts.get("limit")
        qs = EmailNotification.objects.all()
        if to:
            qs = qs.filter(to_email__iexact=to)
        counts = (
            qs.values("status").order_by("status").annotate(c=models.Count("id"))
        )
        self.stdout.write("Counts by status:")
        for row in counts:
            self.stdout.write(f"  {row['status']}: {row['c']}")
        self.stdout.write("")
        self.stdout.write("Recent notifications:")
        for n in qs.order_by("-id")[:limit]:
            self.stdout.write(
                f"[{n.id}] {n.status} to={n.to_email} subject={n.subject!r} retries={n.retry_count}"
            )
