import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

TABLE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class Command(BaseCommand):
    help = (
        "Introspecciona la BD legacy (alias 'legacy' en DATABASES, ver .env) "
        "para preparar los scripts de BBDD-Migration/. Sin --tables, lista "
        "todas las tablas con su numero de filas. Con --tables, muestra el "
        "DESCRIBE de cada tabla indicada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tables",
            type=str,
            default="",
            help="Nombres de tabla separados por coma para describir en detalle.",
        )

    def handle(self, *args, **options):
        tables_arg = options["tables"].strip()
        requested = [t.strip() for t in tables_arg.split(",") if t.strip()]
        for table in requested:
            if not TABLE_NAME_RE.match(table):
                raise CommandError(f"Nombre de tabla invalido: {table!r}")

        with connections["legacy"].cursor() as cursor:
            if requested:
                for table in requested:
                    self.stdout.write(self.style.MIGRATE_HEADING(f"\n-- {table} --"))
                    cursor.execute(f"DESCRIBE `{table}`")
                    for row in cursor.fetchall():
                        self.stdout.write("  " + "  ".join(str(v) for v in row))
            else:
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                self.stdout.write(self.style.MIGRATE_HEADING(f"Tablas encontradas: {len(tables)}"))
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    count = cursor.fetchone()[0]
                    self.stdout.write(f"  {table}: {count} filas")
