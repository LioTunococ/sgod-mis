## Email Notifications Module

This project now includes a simple email-only notification system (`notifications` app).

### Model
`EmailNotification` stores queued emails with fields:
- `to_email` – recipient address.
- `subject`, `body` – email content.
- `status` – `pending`, `sent`, or `failed`.
- `error_message` – capture send errors.
- `created_at`, `sent_at` timestamps.

### School Profile Integration
`SchoolProfile` has a new field: `notification_email` (optional). Users can set this via the School Profile edit page. Use this address for system notices (deadlines, reminders, etc.).

### Services
`notifications/services.py` provides helpers:
```python
from notifications.services import send_email_now, queue_email, send_all_pending

send_email_now(
    to_email="recipient@example.com",
    subject="Reminder",
    body="Please complete your quarterly submission."
)
```
If you prefer batching:
```python
queue_email("recipient@example.com", "Subject", "Body")
send_all_pending()  # processes pending items
```

### Admin
`EmailNotification` is registered in Django admin for monitoring status and failures.

### Configuration
Ensure email settings exist in `settings.py`:
```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"  # or console backend for dev
DEFAULT_FROM_EMAIL = "no-reply@yourdomain.example"
EMAIL_HOST = "smtp.yourprovider.example"
EMAIL_PORT = 587
EMAIL_HOST_USER = "smtp-user"
EMAIL_HOST_PASSWORD = "smtp-password"
EMAIL_USE_TLS = True
```
For local development you may swap backend:
```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

### Usage Example (sending to a school's notification email)
```python
from notifications.services import send_email_now
profile = school.profile  # assuming school has profile
if profile.notification_email:
    send_email_now(
        to_email=profile.notification_email,
        subject="Quarterly Report Open",
        body="The submission window is now open. Please log in to complete your forms."
    )
```

### Future Enhancements (optional)
- Add a management command to process pending queue via cron.
- Template-based emails (HTML) & context rendering.
- Batch grouping & rate limiting.
- Per-school notification preferences.

---
Minimal, email-only implementation – ready for immediate use.
