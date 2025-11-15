from __future__ import annotations

from django.db import models


class District(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Section(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code.upper()} - {self.name}"


class School(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    division = models.CharField(max_length=255, blank=True)
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="schools",
        null=True,
        blank=True,
    )
    school_type = models.CharField(max_length=64, blank=True)
    min_grade = models.PositiveSmallIntegerField(null=True, blank=True)
    max_grade = models.PositiveSmallIntegerField(null=True, blank=True)
    implements_adm = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.name} ({self.code})"

    @property
    def grade_span_label(self) -> str:
        profile = getattr(self, "profile", None)
        start = getattr(profile, "grade_span_start", None)
        end = getattr(profile, "grade_span_end", None)
        if start is not None and end is not None:
            return f"G{start}-G{end}"
        if self.min_grade is None or self.max_grade is None:
            return ""
        return f"G{self.min_grade}-G{self.max_grade}"


class SchoolProfile(models.Model):
    school = models.OneToOneField(
        School,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    head_name = models.CharField(max_length=255, blank=True)
    head_contact = models.CharField(max_length=255, blank=True)
    grade_span_start = models.PositiveSmallIntegerField(null=True, blank=True)
    grade_span_end = models.PositiveSmallIntegerField(null=True, blank=True)
    strands = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["school__name"]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"SchoolProfile({self.school.name})"

    def grade_span_label(self) -> str:
        if self.grade_span_start is None or self.grade_span_end is None:
            return ""
        return f"G{self.grade_span_start}-G{self.grade_span_end}"
