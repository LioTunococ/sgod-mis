from __future__ import annotations

from typing import Optional
from django.conf import settings
from .models import EmailNotification
from django.db.models import Q


def queue_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> EmailNotification:
    """Create a pending email notification.

    Duplicate suppression: if an identical pending notification (same to_email + subject)
    already exists, do not create a new one; instead return existing.
    """
    existing = EmailNotification.objects.filter(
        to_email__iexact=to_email,
        subject=subject,
        status=EmailNotification.Status.PENDING,
    ).first()
    if existing:
        return existing
    notif = EmailNotification.objects.create(
        to_email=to_email,
        subject=subject,
        body=body,
        html_body=html_body or "",
    )
    # Optional: send immediately if configured (useful on platforms without a scheduler)
    try:
        if getattr(settings, "NOTIFICATIONS_SEND_IMMEDIATELY", False):
            notif.send()
    except Exception:
        pass
    return notif


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
