from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts import roles, scope
from accounts.context_processors import user_role_context
from accounts.models import UserProfile
from accounts.views import post_login_redirect
from organizations.models import District, School, Section
from submissions.models import FormTemplate, Period, Submission

User = get_user_model()


class ScopeTests(TestCase):
    def setUp(self):
        self.district_flora, _ = District.objects.get_or_create(code="flora", defaults={"name": "Flora"})
        self.district_luna, _ = District.objects.get_or_create(code="luna", defaults={"name": "Luna"})

        self.school_flora, _ = School.objects.get_or_create(code="flora-es", defaults={"name": "Flora ES", "district": self.district_flora})
        if self.school_flora.name != "Flora ES" or self.school_flora.district_id != self.district_flora.id:
            self.school_flora.name = "Flora ES"
            self.school_flora.district = self.district_flora
            self.school_flora.save(update_fields=["name", "district"])
        self.school_luna, _ = School.objects.get_or_create(code="luna-es", defaults={"name": "Luna ES", "district": self.district_luna})
        if self.school_luna.name != "Luna ES" or self.school_luna.district_id != self.district_luna.id:
            self.school_luna.name = "Luna ES"
            self.school_luna.district = self.district_luna
            self.school_luna.save(update_fields=["name", "district"])

        self.section, _ = Section.objects.get_or_create(code="smme", defaults={"name": "SMME"})
        today = timezone.now().date()
        self.period = Period.objects.create(
            label="Q1",
            school_year_start=2025,
            quarter_tag='Q1',
            display_order=1,
            is_active=True,
        )
        self.form = FormTemplate.objects.create(
            section=self.section,
            code="smea-form-1",
            title="SMEA Form 1",
            period_type=FormTemplate.PeriodType.QUARTER,
            open_at=today,
            close_at=today,
        )
        self.submission_flora = Submission.objects.create(
            school=self.school_flora,
            form_template=self.form,
            period=self.period,
        )
        self.submission_luna = Submission.objects.create(
            school=self.school_luna,
            form_template=self.form,
            period=self.period,
        )

    def _create_user(self, username: str, **profile_kwargs) -> User:
        user = User.objects.create_user(username=username, password="pass123")
        profile = roles.get_profile(user)
        if profile_kwargs.get("school"):
            profile.school = profile_kwargs["school"]
        if profile_kwargs.get("districts") is not None:
            profile.districts.set(profile_kwargs["districts"])
        if profile_kwargs.get("section_admin_codes") is not None:
            profile.section_admin_codes = profile_kwargs["section_admin_codes"]
        if profile_kwargs.get("is_sgod_admin") is not None:
            profile.is_sgod_admin = profile_kwargs["is_sgod_admin"]
        profile.save()
        return user

    def test_school_head_scope(self):
        user = self._create_user("school_head", school=self.school_flora)
        schools = list(scope.scope_schools(user))
        submissions = list(scope.scope_submissions(user))
        self.assertEqual([self.school_flora], schools)
        self.assertEqual([self.submission_flora], submissions)
        self.assertTrue(roles.is_school_head(user))

    def test_psds_scope(self):
        user = self._create_user("psds_user", districts=[self.district_flora])
        school_codes = set(scope.scope_schools(user).values_list("code", flat=True))
        submission_ids = set(scope.scope_submissions(user).values_list("id", flat=True))
        self.assertEqual({"flora-es"}, school_codes)
        self.assertEqual({self.submission_flora.id}, submission_ids)
        self.assertTrue(roles.is_psds(user))

    def test_section_admin_scope_all(self):
        user = self._create_user("section_admin", section_admin_codes=["smme"])
        school_codes = set(scope.scope_schools(user).values_list("code", flat=True))
        submission_ids = set(scope.scope_submissions(user).values_list("id", flat=True))
        self.assertEqual({"flora-es", "luna-es"}, school_codes)
        self.assertEqual({self.submission_flora.id, self.submission_luna.id}, submission_ids)
        self.assertTrue(roles.is_section_admin(user, "smme"))

    def test_sgod_admin_scope_all(self):
        user = self._create_user("sgod_admin_user", is_sgod_admin=True)
        school_codes = set(scope.scope_schools(user).values_list("code", flat=True))
        submission_ids = set(scope.scope_submissions(user).values_list("id", flat=True))
        self.assertEqual({"flora-es", "luna-es"}, school_codes)
        self.assertEqual({self.submission_flora.id, self.submission_luna.id}, submission_ids)
        self.assertTrue(roles.is_sgod_admin(user))




class ContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="reviewer", password="pass123")
        profile = roles.get_profile(self.user)
        profile.is_sgod_admin = True
        profile.save(update_fields=["is_sgod_admin", "updated_at"])

    def test_user_role_context_anonymous(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        ctx = user_role_context(request)
        self.assertFalse(ctx["role_flags"]["is_sgod_admin"])
        self.assertEqual(ctx["assigned_district_ids"], [])

    def test_user_role_context_authenticated(self):
        request = self.factory.get("/")
        request.user = self.user
        ctx = user_role_context(request)
        self.assertTrue(ctx["role_flags"]["is_sgod_admin"])
        self.assertIsNone(ctx["current_school"])


class PostLoginRedirectTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.section = Section.objects.create(code="smme", name="SMME")
        self.district = District.objects.create(code="north", name="North District")
        self.school = School.objects.create(code="north-es", name="North ES", district=self.district)

    def _create_user(self, username: str, *, school=None, districts=None, section_codes=None, is_sgod_admin=False):
        user = get_user_model().objects.create_user(username=username, password="pass123")
        profile = roles.get_profile(user)
        if school is not None:
            profile.school = school
        if districts is not None:
            profile.districts.set(districts)
        if section_codes is not None:
            profile.section_admin_codes = section_codes
        if is_sgod_admin:
            profile.is_sgod_admin = True
        profile.save()
        return user

    def _dispatch(self, user):
        request = self.factory.get("/after-login/")
        request.user = user
        response = post_login_redirect(request)
        return response

    def test_redirect_for_school_head(self):
        user = self._create_user("schoolhead", school=self.school)
        response = self._dispatch(user)
        self.assertEqual(response.url, reverse("school_home"))

    def test_redirect_for_section_admin(self):
        user = self._create_user("sectionadmin", section_codes=["smme"])
        response = self._dispatch(user)
        self.assertEqual(response.url, reverse("review_queue", args=["smme"]))

    def test_redirect_for_psds(self):
        user = self._create_user("psds", districts=[self.district])
        response = self._dispatch(user)
        self.assertEqual(response.url, reverse("smme_kpi_dashboard"))

    def test_redirect_for_sgod_admin(self):
        user = self._create_user("sgod", is_sgod_admin=True)
        response = self._dispatch(user)
        self.assertEqual(response.url, reverse("division_overview"))

    def test_redirect_fallback_no_roles(self):
        user = self._create_user("general")
        response = self._dispatch(user)
        self.assertEqual(response.url, reverse("review_queue", args=["smme"]))

