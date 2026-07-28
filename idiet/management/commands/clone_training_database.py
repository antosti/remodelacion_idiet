import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


VALID_MYSQL_IDENTIFIER = re.compile(r"^[A-Za-z0-9_$]+$")


def quote_identifier(identifier):
    if not VALID_MYSQL_IDENTIFIER.fullmatch(identifier):
        raise CommandError(
            f"El nombre de base de datos {identifier!r} no es un identificador MySQL válido."
        )
    return f"`{identifier}`"


class Command(BaseCommand):
    help = (
        "Crea la base de formación como copia completa de las tablas y datos "
        "de la base principal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Elimina y vuelve a crear la base de formación si ya existe.",
        )

    def handle(self, *args, **options):
        source = settings.DATABASES["default"]
        target = settings.DATABASES["training"]

        if source["ENGINE"] != "django.db.backends.mysql":
            raise CommandError("Este comando solo admite MySQL.")
        if target["ENGINE"] != source["ENGINE"]:
            raise CommandError("Las dos bases deben usar el mismo motor MySQL.")

        connection_keys = ("HOST", "PORT", "USER")
        if any(source.get(key) != target.get(key) for key in connection_keys):
            raise CommandError(
                "La copia SQL requiere que ambas bases estén en el mismo servidor "
                "y sean accesibles con el mismo usuario."
            )

        source_name = source["NAME"]
        target_name = target["NAME"]
        if source_name == target_name:
            raise CommandError("La base de formación no puede ser la base principal.")

        source_sql = quote_identifier(source_name)
        target_sql = quote_identifier(target_name)

        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
                FROM information_schema.SCHEMATA
                WHERE SCHEMA_NAME = %s
                """,
                [source_name],
            )
            schema = cursor.fetchone()
            if schema is None:
                raise CommandError(f"No existe la base principal {source_name!r}.")

            cursor.execute(
                "SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                [target_name],
            )
            target_exists = cursor.fetchone() is not None
            if target_exists and not options["replace"]:
                raise CommandError(
                    f"La base {target_name!r} ya existe. Usa --replace para regenerarla."
                )

            if target_exists:
                cursor.execute(f"DROP DATABASE {target_sql}")

            charset, collation = schema
            cursor.execute(
                f"CREATE DATABASE {target_sql} "
                f"CHARACTER SET {quote_identifier(charset)} "
                f"COLLATE {quote_identifier(collation)}"
            )

            try:
                cursor.execute(
                    """
                    SELECT TABLE_NAME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                    """,
                    [source_name],
                )
                tables = [row[0] for row in cursor.fetchall()]

                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table in tables:
                    table_sql = quote_identifier(table)
                    cursor.execute(
                        f"CREATE TABLE {target_sql}.{table_sql} "
                        f"LIKE {source_sql}.{table_sql}"
                    )
                    cursor.execute(
                        f"INSERT INTO {target_sql}.{table_sql} "
                        f"SELECT * FROM {source_sql}.{table_sql}"
                    )
                    self.stdout.write(f"Copiada: {table}")
            except Exception:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                cursor.execute(f"DROP DATABASE {target_sql}")
                raise
            finally:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        self.stdout.write(
            self.style.SUCCESS(
                f"Base de formación {target_name!r} creada con {len(tables)} tablas."
            )
        )
