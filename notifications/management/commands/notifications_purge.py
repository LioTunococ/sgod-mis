from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import EmailNotification


class Command(BaseCommand):
    help = "Purge SENT notifications older than a specified number of days (default 30)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Age in days after which SENT notifications are purged")
        parser.add_argument("--dry-run", action="store_true", help="Show how many would be deleted without deleting")

    def handle(self, *args, **opts):
        days = opts.get("days")
        cutoff = timezone.now() - timedelta(days=days)
        qs = EmailNotification.objects.filter(status=EmailNotification.Status.SENT, created_at__lt=cutoff)
        count = qs.count()
        if opts.get("dry_run"):
            self.stdout.write(f"[DRY-RUN] Would delete {count} SENT notifications older than {days} days.")
            return
        deleted = qs.delete()[0]
        self.stdout.write(f"Deleted {deleted} SENT notifications older than {days} days.")