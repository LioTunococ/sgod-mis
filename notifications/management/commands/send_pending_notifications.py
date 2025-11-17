from django.core.management.base import BaseCommand
from notifications.services import send_all_pending


class Command(BaseCommand):
    help = "Send all pending email notifications (batched)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max pending emails to attempt in one run")
        parser.add_argument("--dry-run", action="store_true", help="Show count without sending")
        parser.add_argument("--retry-failed", action="store_true", help="Include FAILED items for retry")
        parser.add_argument("--max-retries", type=int, default=None, help="Only retry failures with retry_count less than this number")

    def handle(self, *args, **options):
        limit = options.get("limit")
        dry_run = options.get("dry_run")
        if dry_run:
            from notifications.models import EmailNotification
            base_qs = EmailNotification.objects.filter(status="pending")
            if options.get("retry_failed"):
                from django.db.models import Q
                fq = EmailNotification.objects.filter(status="failed")
                if options.get("max_retries") is not None:
                    fq = fq.filter(retry_count__lt=options["max_retries"])
                total = base_qs.count() + fq.count()
            else:
                total = base_qs.count()
            self.stdout.write(self.style.WARNING(f"Dry run: {total} email(s) would be attempted."))
            return
        sent = send_all_pending(limit=limit, retry_failed=options.get("retry_failed", False), max_retries=options.get("max_retries"))
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} email(s)."))
