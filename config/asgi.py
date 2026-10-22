"""ASGI entry point; choose a different settings module through the environment."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
application = get_asgi_application()
