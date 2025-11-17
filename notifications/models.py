from django.db import models
from django.core.mail import send_mail
from django.utils import timezone


class EmailNotification(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		SENT = "sent", "Sent"
		FAILED = "failed", "Failed"

	to_email = models.EmailField()
	subject = models.CharField(max_length=255)
	body = models.TextField()
	html_body = models.TextField(blank=True)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
	error_message = models.CharField(max_length=512, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	sent_at = models.DateTimeField(null=True, blank=True)
	last_attempt_at = models.DateTimeField(null=True, blank=True)
	retry_count = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):  # pragma: no cover - trivial
		return f"EmailNotification(to={self.to_email}, status={self.status})"

	def send(self, *, fail_silently=False) -> bool:
		if self.status == self.Status.SENT:
			return True
		try:
			send_mail(
				subject=self.subject,
				message=self.body,
				from_email=None,  # use DEFAULT_FROM_EMAIL
				recipient_list=[self.to_email],
				fail_silently=fail_silently,
				html_message=self.html_body or None,
			)
		except Exception as exc:  # pragma: no cover - network dependent
			self.status = self.Status.FAILED
			self.error_message = str(exc)[:500]
			self.retry_count = (self.retry_count or 0) + 1
			self.last_attempt_at = timezone.now()
			self.save(update_fields=["status", "error_message", "retry_count", "last_attempt_at"])
			return False
		else:
			self.status = self.Status.SENT
			self.sent_at = timezone.now()
			self.last_attempt_at = self.sent_at
			self.save(update_fields=["status", "sent_at", "last_attempt_at"])
			return True

	def requeue(self) -> None:
		self.status = self.Status.PENDING
		self.error_message = ""
		self.save(update_fields=["status", "error_message"])


