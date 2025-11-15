from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()


def get_profile(user: User) -> Optional[UserProfile]:
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile
    except UserProfile.DoesNotExist:  # pragma: no cover - fallback
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile


def is_sgod_admin(user: User) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    profile = get_profile(user)
    return bool(profile and profile.is_sgod_admin)


def is_school_head(user: User) -> bool:
    profile = get_profile(user)
    return bool(profile and profile.school) or is_sgod_admin(user)


def is_psds(user: User) -> bool:
    profile = get_profile(user)
    return bool(profile and profile.districts.exists()) or is_sgod_admin(user)


def is_section_admin(user: User, code: Optional[str] = None) -> bool:
    """Return True if user is a Section Admin, optionally for a specific section code.

    Comparison is case-insensitive to avoid mismatches between stored codes
    (e.g., "smme") and lookups (e.g., "SMME"). SGOD admins are always allowed.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if is_sgod_admin(user):
        return True
    profile = get_profile(user)
    if not profile:
        return False
    codes = profile.section_admin_codes or []
    if code is None:
        return bool(codes)
    target = (code or "").strip().upper()
    return any(((c or "").strip().upper() == target) for c in codes)
