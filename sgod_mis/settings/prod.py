from .base import *
import os

# Production overrides using environment variables
DEBUG = os.getenv("DEBUG", "").lower() in {"1", "true", "yes", "on"}

# ALLOWED_HOSTS: comma-separated list, e.g. "example.com,.onrender.com"
ALLOWED_HOSTS = (
	os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []
)

# Security settings (toggleable by env for staging flexibility)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "1").lower() in {"1", "true", "yes", "on"}
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1").lower() in {"1", "true", "yes", "on"}
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "1").lower() in {"1", "true", "yes", "on"}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Static files: collected to STATIC_ROOT and served by WhiteNoise
STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Insert WhiteNoise immediately after SecurityMiddleware
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
	try:
		security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
		MIDDLEWARE.insert(security_index + 1, "whitenoise.middleware.WhiteNoiseMiddleware")
	except ValueError:
		MIDDLEWARE = ["whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE]

# Optional: DATABASE_URL support (falls back to SQLite from base.py)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
	try:
		import dj_database_url  # type: ignore

		DATABASES["default"] = dj_database_url.parse(
			DATABASE_URL,
			conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
			ssl_require=os.getenv("DB_SSL_REQUIRE", "1").lower() in {"1", "true", "yes", "on"},
		)
	except Exception:
		# If package missing or URL invalid, keep SQLite for demo/staging
		pass

# Basic logging suitable for PaaS
LOGGING = {
	"version": 1,
	"disable_existing_loggers": False,
	"handlers": {
		"console": {"class": "logging.StreamHandler"},
	},
	"root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
