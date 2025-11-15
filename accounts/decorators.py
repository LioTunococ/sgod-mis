from __future__ import annotations

from functools import wraps
from typing import Callable

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from organizations.models import School, Section

from . import roles


def require_school_head(*, submission_kwarg: str | None = None, school_kwarg: str | None = None):
    """Allow only School Heads (or SGOD admins) to access the view."""

    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not roles.is_school_head(user):
                raise PermissionDenied("School Head role required.")

            profile = roles.get_profile(user)
            target_school = None

            if submission_kwarg and submission_kwarg in kwargs:
                from submissions.models import Submission  # lazy import

                submission = kwargs[submission_kwarg]
                if not isinstance(submission, Submission):
                    submission = get_object_or_404(Submission, pk=submission)
                kwargs.setdefault("submission_obj", submission)
                target_school = submission.school
            elif school_kwarg and school_kwarg in kwargs:
                target_school = get_object_or_404(School, pk=kwargs[school_kwarg])
            else:
                target_school = profile.school if profile else None

            if roles.is_sgod_admin(user):
                return view_func(request, *args, **kwargs)

            if not profile or not profile.school:
                raise PermissionDenied("No school is associated with your account.")

            if target_school and profile.school_id != target_school.id:
                raise PermissionDenied("You can only act on your assigned school.")

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def require_section_admin(*, section_kwarg: str | None = "section_code", submission_kwarg: str | None = None):
    """Guard views that require Section Admin privileges."""

    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not roles.is_section_admin(user):
                raise PermissionDenied("Section Admin role required.")

            if roles.is_sgod_admin(user):
                return view_func(request, *args, **kwargs)

            section_code = None
            if section_kwarg and section_kwarg in kwargs:
                section = get_object_or_404(Section, code=kwargs[section_kwarg])
                kwargs.setdefault("section_obj", section)
                section_code = section.code
            elif submission_kwarg and submission_kwarg in kwargs:
                from submissions.models import Submission  # lazy import

                submission = kwargs[submission_kwarg]
                if not isinstance(submission, Submission):
                    submission = get_object_or_404(Submission, pk=submission)
                kwargs.setdefault("submission_obj", submission)
                section_code = submission.form_template.section.code

            if section_code and not roles.is_section_admin(user, section_code):
                raise PermissionDenied("You are not an admin for this section.")

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def view_only_psds(view_func: Callable):
    """Restrict a view to PSDS (district supervisors) and SGOD admins."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not (roles.is_psds(user) or roles.is_sgod_admin(user)):
            raise PermissionDenied("PSDS role required.")
        return view_func(request, *args, **kwargs)

    return wrapped
# Backwards-compatible aliases
school_head_required = require_school_head
section_admin_required = require_section_admin


def require_sgod_admin():
    """Restrict a view to SGOD administrators."""

    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not roles.is_sgod_admin(request.user):
                raise PermissionDenied("SGOD access required.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
