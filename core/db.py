"""Unicode search/sort support for the project's SQLite database."""
from django.db.models import CharField, Func


class Casefold(Func):
    function = "ANALYMARK_CASEFOLD"
    output_field = CharField()


def configure_sqlite(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "ANALYMARK_CASEFOLD", 1, lambda value: value.casefold() if isinstance(value, str) else value,
            deterministic=True,
        )
