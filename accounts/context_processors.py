from __future__ import annotations

from typing import Any, Dict

from . import roles


def user_role_context(request) -> Dict[str, Any]:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "current_school": None,
            "role_flags": {
                "is_school_head": False,
                "is_psds": False,
                "is_section_admin": False,
                "is_sgod_admin": False,
            },
            "section_admin_codes": [],
            "assigned_district_ids": [],
            "profile_alerts": {"missing_profiles": 0, "missing_contacts": 0, "span_mismatches": 0},
        }

    profile = roles.get_profile(user)
    districts = profile.districts.all() if profile else []
    section_codes = list(profile.section_admin_codes or []) if profile else []
    district_ids = list(districts.values_list("id", flat=True)) if profile else []

    profile_alerts = {"missing_profiles": 0, "missing_contacts": 0, "span_mismatches": 0}
    if roles.is_sgod_admin(user):
        from organizations.models import SchoolProfile

        qs = SchoolProfile.objects.select_related("school")
        profile_alerts["missing_profiles"] = qs.filter(head_name__exact="", head_contact__exact="").count()
        profile_alerts["missing_contacts"] = qs.filter(head_contact__exact="").count()

        def _span_mismatch(profile):
            school = profile.school
            start = profile.grade_span_start or school.min_grade
            end = profile.grade_span_end or school.max_grade
            if start is None or end is None:
                return False
            slp_rows = school.submissions.filter(status__in=["submitted", "noted"]).values_list("form1_slp_rows__grade_label", flat=True)
            for label in slp_rows:
                if label:
                    digits = "".join(ch for ch in str(label) if ch.isdigit())
                    if digits:
                        grade = int(digits)
                        if not (start <= grade <= end):
                            return True
            return False

        profile_alerts["span_mismatches"] = sum(1 for profile in qs if _span_mismatch(profile))

    role_flags = {
        "is_school_head": roles.is_school_head(user),
        "is_psds": roles.is_psds(user),
        "is_section_admin": roles.is_section_admin(user),
        "is_sgod_admin": roles.is_sgod_admin(user),
    }

    return {
        "current_school": profile.school if profile else None,
        "role_flags": role_flags,
        "section_admin_codes": section_codes,
        "assigned_district_ids": district_ids,
        "profile_alerts": profile_alerts,
    }
