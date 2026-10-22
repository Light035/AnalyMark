"""Local development only; never use this module as deployment configuration."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in {"true", "1", "yes"}

if not SECRET_KEY:  # noqa: F405
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG is false.")
    # Public, development-only fallback. This is not a deployment secret.
    SECRET_KEY = "django-insecure-local-development-only-analy-mark-do-not-deploy"

if not ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
