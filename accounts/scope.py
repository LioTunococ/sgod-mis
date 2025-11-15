from __future__ import annotations

from django.contrib.auth import get_user_model

from organizations.models import School

from . import roles

User = get_user_model()


def scope_schools(user: User):
    if not getattr(user, "is_authenticated", False):
        return School.objects.none()

    qs = School.objects.all()

    if roles.is_sgod_admin(user) or roles.is_section_admin(user):
        return qs

    profile = roles.get_profile(user)
    if not profile:
        return School.objects.none()

    if profile.school_id:
        return qs.filter(pk=profile.school_id)

    if profile.districts.exists():
        return qs.filter(district__in=profile.districts.all())

    return School.objects.none()


def scope_submissions(user: User):
    from submissions.models import Submission

    if not getattr(user, "is_authenticated", False):
        return Submission.objects.none()

    qs = Submission.objects.all()

    if roles.is_sgod_admin(user) or roles.is_section_admin(user):
        return qs

    profile = roles.get_profile(user)
    if not profile:
        return Submission.objects.none()

    if profile.school_id:
        return qs.filter(school_id=profile.school_id)

    if profile.districts.exists():
        return qs.filter(school__district__in=profile.districts.all())

    return Submission.objects.none()
