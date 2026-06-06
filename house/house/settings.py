"""
Django settings for house project.
"""

from pathlib import Path
from decimal import Decimal
import os
from dotenv import load_dotenv


load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# DEBUG = "True" if os.getenv("DEBUG", "False") == "True" else False
DEBUG = True
REDIS_HOST = os.getenv("REDIS_URL")

# twilio settings
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TWILIO_WHATSAPP_FROM = os.getenv(
    "TWILIO_WHATSAPP_FROM",
    f"whatsapp:{TWILIO_PHONE_NUMBER}" if TWILIO_PHONE_NUMBER else None,
)
LANDLORD_WHATSAPP_NUMBER = os.getenv("LANDLORD_WHATSAPP_NUMBER")
LANDLORD_SMS_NUMBER = os.getenv("LANDLORD_SMS_NUMBER")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "textbee")
SMS_MAX_LENGTH = int(os.getenv("SMS_MAX_LENGTH", "160"))
SMS_RETRY_MAX_ATTEMPTS = int(os.getenv("SMS_RETRY_MAX_ATTEMPTS", "5"))
SMS_RETRY_INTERVAL_MINUTES = int(os.getenv("SMS_RETRY_INTERVAL_MINUTES", "6"))
TEXTBEE_API_KEY = os.getenv("TEXTBEE_API_KEY")
TEXTBEE_DEVICE_ID = os.getenv("TEXTBEE_DEVICE_ID")
TEXTBEE_BASE_URL = os.getenv("TEXTBEE_BASE_URL", "https://api.textbee.dev/api/v1")
TEXTBEE_SIM_SUBSCRIPTION_ID = os.getenv("TEXTBEE_SIM_SUBSCRIPTION_ID")

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@propertyempire.local")

PLATFORM_TRANSACTION_FEE_RATE = Decimal(os.getenv("PLATFORM_TRANSACTION_FEE_RATE", "0.01"))
LANDLORD_MONTHLY_SUBSCRIPTION = Decimal(os.getenv("LANDLORD_MONTHLY_SUBSCRIPTION", "200.00"))

CSRF_TRUSTED_ORIGINS = [
    "https://propertyempire.onrender.com",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "propertyempire.onrender.com", ".onrender.com"]


CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "https://propertyempire.onrender.com",
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = False

# if tab is closed in the browser the user is logged out
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 30  # 30 minutes
# always ask for authentication after 5 minutes of inactivity
SESSION_SAVE_EVERY_REQUEST = True


INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tennants",
    "guesthouse",
    "rest_framework",
    "rest_framework.authtoken",
    "phonenumber_field",
    "django_filters",
    "rest_framework_simplejwt",
    "django_redis",
    "corsheaders",
    "django_extensions",
]


# Unfold admin configuration
UNFOLD = {
    "SITE_TITLE": "Property Empire",
    "SITE_HEADER": "Property Management",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Property Management",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Flat buildings",
                        "icon": "apartment",
                        "link": "/admin/tennants/flatbuilding/",
                    },
                    {
                        "title": "Houses",
                        "icon": "home",
                        "link": "/admin/tennants/house/",
                    },
                ],
            },
            {
                "title": "Tennants",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Tenants",
                        "icon": "people",
                        "link": "/admin/tennants/tenant/",
                    },
                ],
            },
            {
                "title": "Payments",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Rent payments",
                        "icon": "payments",
                        "link": "/admin/tennants/payment/",
                    },
                    {
                        "title": "Rent charges",
                        "icon": "history",
                        "link": "/admin/tennants/rentcharge/",
                    },
                ],
            },
            {
                "title": "Guest House",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/guesthouse/",
                    },
                    {
                        "title": "Rooms",
                        "icon": "bed",
                        "link": "/admin/guesthouse/room/",
                    },
                    {
                        "title": "Room Types",
                        "icon": "category",
                        "link": "/admin/guesthouse/roomtype/",
                    },
                    {
                        "title": "Guests",
                        "icon": "people",
                        "link": "/admin/guesthouse/guest/",
                    },
                    {
                        "title": "Bookings",
                        "icon": "event",
                        "link": "/admin/guesthouse/booking/",
                    },
                    {
                        "title": "Check In / Out",
                        "icon": "login",
                        "link": "/guesthouse/reception/",
                    },
                    {
                        "title": "Payments",
                        "icon": "payments",
                        "link": "/admin/guesthouse/guestpayment/",
                    },
                    {
                        "title": "Housekeeping",
                        "icon": "cleaning",
                        "link": "/admin/guesthouse/housekeepingtask/",
                    },
                    {
                        "title": "Maintenance",
                        "icon": "build",
                        "link": "/admin/guesthouse/roommaintenance/",
                    },
                    {
                        "title": "Reports",
                        "icon": "analytics",
                        "link": "/guesthouse/reports/",
                    },
                ],
            },
        ],
    },
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CACHE_TTL = 60 * 15  # 15 minutes


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "house.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "house.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "OPTIONS": {
            "sslmode": os.environ.get("DB_SSLMODE", "require"),
        },
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# login urls
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

KEEPALIVE_URL = "http://propertyempire.onrender.com/api/health/"
