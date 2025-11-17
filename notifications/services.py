from __future__ import annotations

from typing import Optional
from .models import EmailNotification


def queue_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> EmailNotification:
    """Create a pending email notification without sending immediately."""
    return EmailNotification.objects.create(
        to_email=to_email,
        subject=subject,
        body=body,
        html_body=html_body or "",
    )


def send_email_now(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Create and send an email notification immediately."""
    notif = queue_email(to_email, subject, body, html_body)
    return notif.send()


def send_all_pending(limit: Optional[int] = 50, *, retry_failed: bool = False, max_retries: Optional[int] = None) -> int:
    """Attempt to send queued notifications.

    - When retry_failed=True, include FAILED items up to max_retries.
    - Returns count successfully sent.
    """
    from django.db.models import Q

    base_q = Q(status=EmailNotification.Status.PENDING)
    if retry_failed:
        base_q |= Q(status=EmailNotification.Status.FAILED)
        qs = EmailNotification.objects.filter(base_q).order_by("created_at")
        if max_retries is not None:
            qs = qs.filter(retry_count__lt=max_retries)
    else:
        qs = EmailNotification.objects.filter(status=EmailNotification.Status.PENDING).order_by("created_at")

    if limit is not None:
        qs = qs[:limit]
    sent_count = 0
    for notif in qs:
        if notif.status == EmailNotification.Status.FAILED:
            # Transition to pending prior to retry
            notif.requeue()
        if notif.send():
            sent_count += 1
    return sent_count
