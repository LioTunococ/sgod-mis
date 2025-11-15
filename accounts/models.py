from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from organizations.models import District, School, Section


class SchoolUserRole(models.Model):
    class Role(models.TextChoices):
        SCHOOL_HEAD = "school_head", _("School Head")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_roles",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.SCHOOL_HEAD)
    is_primary = models.BooleanField(
        default=True,
        help_text="Use to flag the primary school assignment for the user.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "school", "role")
        ordering = ["school__name", "user__username"]

    def __str__(self) -> str:  # pragma: no cover - legacy helper
        return f"{self.user} @ {self.school} ({self.get_role_display()})"


class SectionUserRole(models.Model):
    class Role(models.TextChoices):
        SECTION_ADMIN = "section_admin", _("Section Admin")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="section_roles",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.SECTION_ADMIN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "section", "role")
        ordering = ["section__code", "user__username"]

    def __str__(self) -> str:  # pragma: no cover - legacy helper
        return f"{self.user} @ {self.section} ({self.get_role_display()})"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    school = models.ForeignKey(
        School,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    districts = models.ManyToManyField(District, blank=True, related_name="profiles")
    is_sgod_admin = models.BooleanField(default=False)
    section_admin_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Profile({self.user})"

    def add_section_code(self, code: str) -> None:
        if not code:
            return
        codes = set(self.section_admin_codes or [])
        codes.add(code)
        self.section_admin_codes = sorted(codes)
        self.save(update_fields=["section_admin_codes", "updated_at"])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)
