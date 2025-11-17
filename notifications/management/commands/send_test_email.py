from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from notifications.services import send_email_now


class Command(BaseCommand):
    help = "Send a test email to verify backend configuration"

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient email address")
        parser.add_argument("--subject", default="SGOD MIS Email Test")
        parser.add_argument("--body", default="Test — SGOD MIS is configured.")
        parser.add_argument("--html", action="store_true", help="Include HTML body as well")
        parser.add_argument("--direct", action="store_true", help="Send directly (bypass queue)")

    def handle(self, *args, **opts):
        to = opts["to"]
        subject = opts["subject"]
        body = opts["body"]
        html = (f"<p><strong>{body}</strong></p>") if opts.get("html") else None
        backend = settings.EMAIL_BACKEND

        if opts.get("direct"):
            try:
                send_mail(subject, body, None, [to], html_message=html)
            except Exception as exc:
                raise CommandError(f"Direct send failed: {exc}")
            self.stdout.write(self.style.SUCCESS(f"✓ Direct test email sent to {to} using backend {backend}"))
            return

        ok = send_email_now(to, subject, body, html)
        if ok:
            self.stdout.write(self.style.SUCCESS(f"✓ Queued+sent test email to {to} using backend {backend}"))
        else:
            self.stderr.write(self.style.ERROR(f"✗ Failed to send email to {to} using backend {backend}"))
