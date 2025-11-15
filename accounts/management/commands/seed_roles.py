from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import UserProfile
from organizations.models import District, School

User = get_user_model()

PASSWORD_ENV_KEY = "SEED_USERS_PASSWORD"
DEFAULT_PASSWORD = "TestPass123"

DISTRICT_FIXTURES = [
    ("flora", "Flora"),
    ("sta-marcela", "Sta. Marcela"),
    ("luna", "Luna"),
    ("pudtol", "Pudtol"),
    ("kabugao-1", "Kabugao 1"),
    ("kabugao-2", "Kabugao 2"),
    ("northern-conner", "Northern Conner"),
    ("southern-conner", "Southern Conner"),
    ("upper-calanasan", "Upper Calanasan"),
    ("lower-calanasan", "Lower Calanasan"),
]


class Command(BaseCommand):
    help = "Seed demo users and profiles for role-based scoping"

    def handle(self, *args, **options):
        password = os.getenv(PASSWORD_ENV_KEY, DEFAULT_PASSWORD)
        self.stdout.write(self.style.MIGRATE_HEADING(f"Using seed user password: {password}"))

        districts = {code: self._ensure_district(code, name) for code, name in DISTRICT_FIXTURES}
        luna_school = self._ensure_school("luna-es", "Luna Elementary School", districts.get("luna"))

        self._create_sgod_admin(password)
        self._create_psds("psds_flora", "flora", districts, password)
        self._create_psds("psds_luna", "luna", districts, password)
        self._create_school_head("schoolhead_luna", luna_school, password)
        self._create_section_admin("section_admin_smme", ["smme"], password)

        self.stdout.write(
            "Do you want me to also include seed users (like psds_flora, schoolhead_luna, sgod_admin, etc.) mapped to those 10 seeded districts, so you can demo role scoping right away?"
        )
        self.stdout.write(self.style.SUCCESS("Role seed complete."))

    def _ensure_district(self, code: str, name: str) -> District:
        district, _ = District.objects.get_or_create(code=code, defaults={"name": name})
        if district.name != name:
            district.name = name
            district.save(update_fields=["name"])
        return district

    def _ensure_school(self, code: str, name: str, district: District | None) -> School:
        defaults = {"name": name}
        if district:
            defaults["district"] = district
        school, created = School.objects.get_or_create(code=code, defaults=defaults)
        update_fields = []
        if school.name != name:
            school.name = name
            update_fields.append("name")
        if district and school.district != district:
            school.district = district
            update_fields.append("district")
        if update_fields:
            school.save(update_fields=update_fields)
        return school

    def _get_user_and_profile(self, username: str, email: str, password: str, *, is_staff=False, is_superuser=False) -> UserProfile:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": is_staff, "is_superuser": is_superuser},
        )
        if created:
            user.set_password(password)
        else:
            if is_staff and not user.is_staff:
                user.is_staff = True
            if is_superuser and not user.is_superuser:
                user.is_superuser = True
            if not user.check_password(password):
                user.set_password(password)
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def _create_sgod_admin(self, password: str) -> None:
        profile = self._get_user_and_profile(
            username="sgod_admin",
            email="sgod_admin@example.com",
            password=password,
            is_staff=True,
            is_superuser=True,
        )
        if not profile.is_sgod_admin:
            profile.is_sgod_admin = True
            profile.save(update_fields=["is_sgod_admin", "updated_at"])

    def _create_psds(self, username: str, district_code: str, districts: dict[str, District], password: str) -> None:
        profile = self._get_user_and_profile(
            username=username,
            email=f"{username}@example.com",
            password=password,
            is_staff=True,
        )
        district = districts.get(district_code)
        if district:
            profile.districts.set([district])
        profile.save(update_fields=["updated_at"])

    def _create_school_head(self, username: str, school: School, password: str) -> None:
        profile = self._get_user_and_profile(
            username=username,
            email=f"{username}@example.com",
            password=password,
            is_staff=True,
        )
        if profile.school_id != school.id:
            profile.school = school
            profile.save(update_fields=["school", "updated_at"])

    def _create_section_admin(self, username: str, section_codes: list[str], password: str) -> None:
        profile = self._get_user_and_profile(
            username=username,
            email=f"{username}@example.com",
            password=password,
            is_staff=True,
        )
        profile.section_admin_codes = sorted(set(section_codes))
        profile.save(update_fields=["section_admin_codes", "updated_at"])
