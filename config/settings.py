import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Dev-only settings. This is a take-home scaffold, not production.
SECRET_KEY = "dev-only-insecure-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "notification",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "avicenna"),
        "USER": os.getenv("POSTGRES_USER", "avicenna"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "avicenna"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = False
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "60"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "50"))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
if os.getenv("CELERY_WORKER_POOL"):
    CELERY_WORKER_POOL = os.environ["CELERY_WORKER_POOL"]
elif os.name == "nt":
    CELERY_WORKER_POOL = "solo"
CELERY_TASK_DEFAULT_QUEUE = "notifications"
CELERY_BEAT_SCHEDULE = {
    "enqueue-due-notifications-every-minute": {
        "task": "notification.tasks.enqueue_due_notifications",
        "schedule": 60.0,
    },
}

NOTIFICATION_ENQUEUE_BATCH_SIZE = int(
    os.getenv("NOTIFICATION_ENQUEUE_BATCH_SIZE", "100")
)
