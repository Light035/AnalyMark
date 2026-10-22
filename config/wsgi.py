"""WSGI entry point; choose a different settings module through the environment."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
application = get_wsgi_application()
