from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from notifications.models import EmailNotification
from notifications.services import send_email_now


class Command(BaseCommand):
    help = "Comprehensive notifications health check: backend, sender, counts, optional test send."

    def add_arguments(self, parser):
        parser.add_argument("--send-test", action="store_true", help="Send a test email (requires --to)")
        parser.add_argument("--to", dest="to", default=None, help="Recipient for test email")
        parser.add_argument("--html", action="store_true", help="Send HTML test variant")
        parser.add_argument("--subject", default="Notification Health Check", help="Custom subject for test email")
        parser.add_argument("--body", default="This is a test notification email.", help="Custom body text")
        parser.add_argument("--limit", type=int, default=5, help="Show this many recent notifications")

    def handle(self, *args, **opts):
        backend = getattr(settings, "EMAIL_BACKEND", "<unset>")
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "<unset>")
        provider = getattr(settings, "ANYMAIL_PROVIDER", "") or self._infer_provider(backend)
        immediate = getattr(settings, "NOTIFICATIONS_SEND_IMMEDIATELY", False)
        anymail_cfg = getattr(settings, "ANYMAIL", {})

        self.stdout.write("=== Email Backend Configuration ===")
        self.stdout.write(f"EMAIL_BACKEND: {backend}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {default_from}")
        self.stdout.write(f"ANYMAIL_PROVIDER: {provider or '(none)'}")
        if provider:
            masked = {k: ('***' if v else '') for k, v in anymail_cfg.items() if k.endswith('_API_KEY')}
            self.stdout.write(f"ANYMAIL keys present: {masked}")
        self.stdout.write(f"NOTIFICATIONS_SEND_IMMEDIATELY: {immediate}")
        self.stdout.write("")

        qs_all = EmailNotification.objects.all()
        counts = qs_all.values("status").order_by("status").annotate(c=models.Count("id"))
        total = qs_all.count()
        pending = qs_all.filter(status=EmailNotification.Status.PENDING).count()
        failed = qs_all.filter(status=EmailNotification.Status.FAILED).count()
        sent = qs_all.filter(status=EmailNotification.Status.SENT).count()

        self.stdout.write("=== Notification Counts ===")
        self.stdout.write(f"Total: {total}  Pending: {pending}  Failed: {failed}  Sent: {sent}")
        for row in counts:
            self.stdout.write(f"  {row['status']}: {row['c']}")
        self.stdout.write("")

        limit = opts.get("limit")
        self.stdout.write(f"Recent (limit {limit}):")
        for n in qs_all.order_by("-id")[:limit]:
            self.stdout.write(f"[{n.id}] {n.status} to={n.to_email} subject={n.subject!r} retries={n.retry_count}")
        self.stdout.write("")

        if opts.get("send_test"):
            to = opts.get("to")
            if not to:
                self.stderr.write("--send-test requires --to <recipient>")
                return
            subject = opts.get("subject")
            body = opts.get("body")
            html_body = None
            if opts.get("html"):
                html_body = f"<html><body><h2>{subject}</h2><p>{body}</p><p><em>HTML test variant.</em></p></body></html>"
            self.stdout.write(f"Sending test email to {to}...")
            try:
                ok = send_email_now(to, subject, body, html_body)
                self.stdout.write("Test email queued and sent successfully" if ok else "Test email queued; send attempt failed")
            except Exception as e:
                self.stderr.write(f"Test send exception: {e}")

    @staticmethod
    def _infer_provider(backend: str) -> str:
        if ".backends.sendgrid" in backend:
            return "sendgrid"
        if ".backends.mailgun" in backend:
            return "mailgun"
        if ".backends.mailjet" in backend:
            return "mailjet"
        return ""