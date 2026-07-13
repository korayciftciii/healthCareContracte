"""
Django settings for config project.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Hestia'nın Nginx'i SSL'i sonlandırıp bize düz HTTP ile proxy_pass yapacak;
# Django'nun isteğin aslında HTTPS olduğunu anlaması için bu gerekli
# (admin login/CSRF ve "secure cookie" davranışı için önemli).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "companies",
    "geo",
    "products",
    "institutions",
    "scraper",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Next.js <-> Django auth ---
NEXTJS_MASTER_TOKEN = env("NEXTJS_MASTER_TOKEN")


# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.v1.authentication.StaticBearerTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.v1.pagination.StandardResultsSetPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "PAGE_SIZE": 20,
}


# --- tamamlayicisaglik.com scraper config ---
# All paths below confirmed working via direct testing (no cookies/CSRF header
# required for these GET endpoints). See isterler.md for the captured evidence.
SCRAPER_CONFIG = {
    "BASE_URL": env("TSS_BASE_URL", default="https://www.tamamlayicisaglik.com"),
    "COMPANY_LIST_PATH": env(
        "TSS_COMPANY_LIST_PATH", default="/internal-api/company-list-results"
    ),
    "INSTITUTION_LIST_PATH": env(
        "TSS_INSTITUTION_LIST_PATH", default="/internal-api/search-hospital"
    ),
    "CITY_LIST_PATH": env("TSS_CITY_LIST_PATH", default="/internal-api/cities"),
    "DISTRICT_LIST_PATH": env("TSS_DISTRICT_LIST_PATH", default="/internal-api/districts"),
    "HOSPITAL_TYPES_PATH": env("TSS_HOSPITAL_TYPES_PATH", default="/internal-api/hospital-types"),
    "NETWORKS_PATH": env("TSS_NETWORKS_PATH", default="/internal-api/networks"),
    "DEFAULT_PAGE_SIZE": env.int("TSS_PAGE_SIZE", default=50),
    "REQUEST_DELAY_SECONDS": env.float("TSS_REQUEST_DELAY_SECONDS", default=0.5),
    "REQUEST_TIMEOUT_SECONDS": env.int("TSS_REQUEST_TIMEOUT_SECONDS", default=10),
    "REQUEST_HEADERS": env.json("TSS_EXTRA_HEADERS", default={}),
    # Confirmed empirically: cityId in tamamlayicisaglik's API == Turkish plate code (plaka kodu).
    "CITY_ID_MODE": env("TSS_CITY_ID_MODE", default="plate_code"),
}


# --- django-unfold ---
UNFOLD = {
    "SITE_TITLE": "Sağlık Kurumları Anlaşma Paneli",
    "SITE_HEADER": "Sağlık Kurumları Anlaşma Paneli",
    "SITE_SYMBOL": "local_hospital",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
}
