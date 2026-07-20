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
    "daphne",
    "unfold",
    "channels",
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
    "drf_spectacular",
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
ASGI_APPLICATION = "config.asgi.application"


# Database
# Ayrık DB_* değişkenleri tercih edilir — DATABASE_URL tek bir string olduğu için
# şifredeki özel karakterler (/, #, ?, | vb.) URL parse'ını kırabiliyor (yaşandı).
# DB_NAME verilmişse onlar kullanılır, yoksa DATABASE_URL'e (yerel geliştirme) düşülür.
if env("DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }
else:
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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# --- API dokümantasyonu (drf-spectacular) ---
SPECTACULAR_SETTINGS = {
    "TITLE": "Sağlık Kurumları Anlaşma Takip Sistemi API",
    "DESCRIPTION": (
        "Sigorta şirketlerinin (AXA, HDI, Acıbadem, Türkiye, Anadolu, Allianz, Mapfre) "
        "TSS/ÖSS ürünlerinde anlaşmalı olduğu sağlık kurumlarını sorgulamak için Next.js "
        "backend'inin kullandığı salt-okunur API. Tüm endpoint'ler "
        "`Authorization: Bearer <NEXTJS_MASTER_TOKEN>` header'ı gerektirir."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
}




# --- django-unfold ---
UNFOLD = {
    "SITE_TITLE": "Sağlık Kurumları Anlaşma Paneli",
    "SITE_HEADER": "Sağlık Kurumları Anlaşma Paneli",
    "SITE_SYMBOL": "local_hospital",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Canlı İzleme & Tarama",
                "separator": True,
                "items": [
                    {
                        "title": "Canlı Log Takibi (Stream)",
                        "icon": "terminal",
                        "link": "/admin/scraper/scrapejob/log-stream/",
                    },
                    {
                        "title": "Tarama İşleri",
                        "icon": "work",
                        "link": "/admin/scraper/scrapejob/",
                    },
                ],
            },
        ],
    },
}

