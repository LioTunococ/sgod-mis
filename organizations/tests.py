from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile

from .models import District, School, SchoolProfile


class SchoolModelTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(code="flora", defaults={"name": "Flora"})

    def test_grade_span_label(self):
        school = School.objects.create(
            code="test-school",
            name="Test School",
            district=self.district,
            min_grade=1,
            max_grade=6,
        )
        self.assertEqual(school.grade_span_label, "G1-G6")

    def test_school_links_to_district(self):
        School.objects.create(code="with-district", name="With District", district=self.district)
        school = School.objects.select_related("district").get(code="with-district")
        self.assertEqual(school.district.name, "Flora")


class SchoolProfileTests(TestCase):
    def test_profile_grade_span_label(self):
        district = District.objects.create(code="north", name="North")
        school = School.objects.create(code="north-es", name="North ES", district=district)
        profile = SchoolProfile.objects.create(
            school=school,
            head_name="Alex Rivera",
            grade_span_start=1,
            grade_span_end=6,
            strands=["STEM", "SPED"],
        )
        self.assertEqual(profile.grade_span_label(), "G1-G6")
        self.assertEqual(profile.strands, ["STEM", "SPED"])


class SchoolProfileViewTests(TestCase):
    def setUp(self):
        self.district = District.objects.create(code="south", name="South")
        self.other_district = District.objects.create(code="north", name="North")

        self.school = School.objects.create(code="south-es", name="South ES", district=self.district)
        self.other_school = School.objects.create(code="north-es", name="North ES", district=self.other_district)

        self.profile = SchoolProfile.objects.create(
            school=self.school,
            head_name="Alex Rivera",
            head_contact="alex@example.com",
            grade_span_start=1,
            grade_span_end=6,
            strands=["STEM", "ICT"],
        )
        self.other_profile = SchoolProfile.objects.create(
            school=self.other_school,
            head_name="Maria Cruz",
            head_contact="maria@example.com",
            grade_span_start=7,
            grade_span_end=10,
            strands=["ALS"],
        )

        User = get_user_model()
        self.sgod = User.objects.create_user(username="sgod", password="pass")
        sgod_profile = UserProfile.objects.get(user=self.sgod)
        sgod_profile.is_sgod_admin = True
        sgod_profile.save(update_fields=["is_sgod_admin", "updated_at"])

        self.school_head = User.objects.create_user(username="head", password="pass")
        head_profile = UserProfile.objects.get(user=self.school_head)
        head_profile.school = self.school
        head_profile.save(update_fields=["school", "updated_at"])

    def test_sgod_can_view_and_update_profiles(self):
        self.client.force_login(self.sgod)
        list_url = reverse("organizations:school_profile_list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.school.name)

        edit_url = reverse("organizations:edit_school_profile", args=[self.profile.id])
        payload = {
            "head_name": "Jamie Santos",
            "head_contact": "jamie@example.com",
            "grade_span_start": 1,
            "grade_span_end": 6,
            "strands": "STEM",
        }
        response = self.client.post(edit_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.head_name, "Jamie Santos")

    def test_list_filters_by_search(self):
        self.client.force_login(self.sgod)
        response = self.client.get(reverse("organizations:school_profile_list"), {"q": "Maria"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["profiles"]), [self.other_profile])

    def test_list_filters_by_district(self):
        self.client.force_login(self.sgod)
        response = self.client.get(
            reverse("organizations:school_profile_list"),
            {"district": str(self.other_district.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["profiles"]), [self.other_profile])

    def test_list_filters_by_strand(self):
        self.client.force_login(self.sgod)
        response = self.client.get(
            reverse("organizations:school_profile_list"),
            {"strand": "ALS"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["profiles"]), [self.other_profile])

    def test_non_sgod_is_forbidden(self):
        self.client.force_login(self.school_head)
        list_url = reverse("organizations:school_profile_list")
        self.assertEqual(self.client.get(list_url).status_code, 403)

    def test_school_head_can_edit_own_profile(self):
        self.client.force_login(self.school_head)
        url = reverse("organizations:edit_my_school_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = {
            "head_name": "Jamie Santos",
            "head_contact": "jamie@example.com",
            "grade_span_start": 2,
            "grade_span_end": 7,
            "strands": "STEM, ICT, SPED",
        }
        response = self.client.post(url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School profile updated.")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.head_name, "Jamie Santos")
        self.assertEqual(self.profile.head_contact, "jamie@example.com")
        self.assertEqual(self.profile.grade_span_start, 2)
        self.assertEqual(self.profile.grade_span_end, 7)
        self.assertEqual(self.profile.strands, ["STEM", "ICT", "SPED"])


class DirectoryManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.district = District.objects.create(code="central", name="Central District")
        self.sgod = User.objects.create_user(username="sgod_directory", password="pass")
        sgod_profile = UserProfile.objects.get(user=self.sgod)
        sgod_profile.is_sgod_admin = True
        sgod_profile.save(update_fields=["is_sgod_admin", "updated_at"])

        self.regular_user = User.objects.create_user(username="teacher", password="oldpass")

    def test_create_school(self):
        self.client.force_login(self.sgod)
        url = reverse("organizations:manage_directory")
        payload = {
            "action": "create_school",
            "code": "new-school",
            "name": "New School",
            "division": "Division 1",
            "district": self.district.id,
            "school_type": "Elementary",
            "min_grade": 1,
            "max_grade": 6,
            "implements_adm": True,
        }
        response = self.client.post(url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        school = School.objects.get(code="new-school")
        self.assertTrue(SchoolProfile.objects.filter(school=school).exists())

    def test_reset_password(self):
        self.client.force_login(self.sgod)
        url = reverse("organizations:manage_directory")
        payload = {"action": "reset_password", "username": "teacher", "new_password": "newpass123"}
        response = self.client.post(url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.login(username="teacher", password="newpass123"))

    def test_non_sgod_forbidden(self):
        self.client.force_login(self.regular_user)
        url = reverse("organizations:manage_directory")
        self.assertEqual(self.client.get(url).status_code, 403)
