from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "AnalyMark"

    def ready(self):
        from django.db.backends.signals import connection_created
        from .db import configure_sqlite
        connection_created.connect(configure_sqlite, dispatch_uid="analymark.sqlite.casefold")
