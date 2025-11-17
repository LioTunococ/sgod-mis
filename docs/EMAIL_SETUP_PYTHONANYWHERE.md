# Email Setup on PythonAnywhere

PythonAnywhere (especially free tier) restricts outbound SMTP. Use Anymail HTTP API providers (Mailgun, SendGrid, Mailjet) instead of SMTP.

## Option A: SendGrid via Anymail (recommended)
1. Create a SendGrid account and an API Key with Mail Send permission.
2. Verify a Sender Identity or Domain; note the verified From email.
3. In PythonAnywhere:
   - Go to the app's Web tab → Environment variables (or set in the WSGI file).
   - Add the following environment variables:

   - `ANYMAIL_PROVIDER=sendgrid`
   - `SENDGRID_API_KEY=<your_sendgrid_api_key>`
   - `DEFAULT_FROM_EMAIL=<verified@yourdomain>`

4. Reload the web app in PythonAnywhere.
5. Send a test email:

   ```bash
   python manage.py send_test_email you@example.com --html
   ```

## Option B: Mailgun via Anymail
1. Create a Mailgun account and domain; get the API key.
2. Verify sending domain; note the From domain.
3. Set env vars:

   - `ANYMAIL_PROVIDER=mailgun`
   - `MAILGUN_API_KEY=<your_mailgun_api_key>`
   - `MAILGUN_SENDER_DOMAIN=<your.mailgun.domain>`
   - `DEFAULT_FROM_EMAIL=no-reply@<your.mailgun.domain>`

4. Reload and test:

   ```bash
   python manage.py send_test_email you@example.com --html
   ```

## SMTP (not recommended on free tier)
If you are on a paid PythonAnywhere plan with outbound SMTP allowed, you can configure SMTP instead by setting:

- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS=1` (or `EMAIL_USE_SSL=1`)
- `DEFAULT_FROM_EMAIL=<verified@yourdomain>`

## Operational tips
- Queue processing: `python manage.py send_pending_notifications --retry-failed --limit 100`
- Admin resend/requeue actions available in Django Admin → Email notifications.
- Ensure the school's `notification_email` is set in the School Profile to receive submission updates.
- For production, prefer a domain-verified `DEFAULT_FROM_EMAIL` to avoid spam filtering.
