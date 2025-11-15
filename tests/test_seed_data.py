from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from organizations.models import District
from scripts import seed_data


class SeedDataTests(TestCase):
    def test_seed_run_is_idempotent(self):
        seed_data.run()
        seed_data.run()

        User = get_user_model()
        assert User.objects.filter(username="demo_sgod_admin").exists()
        assert Group.objects.filter(name="SGODAdmin").exists()
        assert District.objects.count() > 0
