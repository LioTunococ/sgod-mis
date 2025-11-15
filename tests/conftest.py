def pytest_configure():
    # Disable all Django migrations during tests to avoid conflicting historical migrations
    # and speed up test database setup. Tables will be created directly from models.
    class DisableMigrations(dict):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    from django.conf import settings
    settings.MIGRATION_MODULES = DisableMigrations()
