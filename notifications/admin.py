from django.contrib import admin
from django.utils.html import format_html
from .models import EmailNotification


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ("to_email", "subject", "status", "retry_count", "created_at", "sent_at")
    list_filter = ("status", "created_at")
    search_fields = ("to_email", "subject", "body")
    readonly_fields = ("created_at", "sent_at", "error_message", "last_attempt_at")
    actions = ["action_resend_now", "action_requeue"]

    def action_resend_now(self, request, queryset):
        success = 0
        for notif in queryset:
            if notif.status == EmailNotification.Status.SENT:
                continue
            if notif.status == EmailNotification.Status.FAILED:
                notif.requeue()
            if notif.send():
                success += 1
        self.message_user(request, f"Resent {success} email(s).")
    action_resend_now.short_description = "Resend selected now"

    def action_requeue(self, request, queryset):
        count = 0
        for notif in queryset.exclude(status=EmailNotification.Status.SENT):
            notif.requeue()
            count += 1
        self.message_user(request, f"Requeued {count} email(s) for sending.")
    action_requeue.short_description = "Requeue selected (set to pending)"
from django.contrib import admin

# Register your models here.
