from __future__ import annotations

from typing import Optional, Set

from django.contrib.auth import get_user_model

from organizations.models import School

from . import roles, scope
from .models import UserProfile

User = get_user_model()


def _get_profile(user: User) -> Optional[UserProfile]:
    return roles.get_profile(user)


def get_primary_school(user: User) -> Optional[School]:
    profile = _get_profile(user)
    return profile.school if profile else None


def get_school_codes(user: User) -> list[str]:
    school = get_primary_school(user)
    return [school.code] if school else []


def get_section_codes(user: User) -> list[str]:
    profile = _get_profile(user)
    return list(profile.section_admin_codes or []) if profile else []


def user_is_school_head(user: User, school: Optional[School] = None) -> bool:
    if not roles.is_school_head(user):
        return False
    if school is None:
        return True
    profile = _get_profile(user)
    return bool(profile and profile.school_id == school.id) or roles.is_sgod_admin(user)


def user_is_section_admin(user: User, section=None) -> bool:
    from organizations.models import Section  # local import to avoid circulars

    section_code = None
    if section is not None:
        if isinstance(section, Section):
            section_code = section.code
        else:
            section_code = section
    return roles.is_section_admin(user, section_code)


def allowed_section_codes(user: User) -> Set[str]:
    return set(get_section_codes(user))


def allowed_school_ids(user: User) -> Set[int]:
    return set(scope.scope_schools(user).values_list("id", flat=True))


def user_is_sgod_admin(user: User) -> bool:
    return roles.is_sgod_admin(user)


def user_is_psds(user: User) -> bool:
    return roles.is_psds(user)
