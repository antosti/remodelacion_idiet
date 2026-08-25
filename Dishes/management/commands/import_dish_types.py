import csv
import io
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Dishes.models import DishCategory, DishCategorySize

# Cada fila exportada es una tupla "(id, ...)" ; los paréntesis solo aparecen
# dentro de literales de texto entre comillas simples, así que basta con no
# cerrar el grupo mientras estemos dentro de una comilla.
TUPLE_RE = re.compile(r"\((?:[^()']|'(?:[^']|'')*')*\)")


def parse_insert_tuples(sql_text):
    rows = []
    for match in TUPLE_RE.finditer(sql_text):
        inner = match.group(0)[1:-1]
        reader = csv.reader(
            io.StringIO(inner), delimiter=',', quotechar="'", doublequote=True, skipinitialspace=True
        )
        row = next(reader)
        # El paréntesis de la lista de columnas en "INSERT INTO ... (col1,col2,...) VALUES"
        # coincide con el mismo patrón que una tupla de valores; se descarta porque su
        # primer campo no es numérico (a diferencia del id de cada fila de datos).
        if not row[0].strip().isdigit():
            continue
        rows.append(row)
    return rows


class Command(BaseCommand):
    help = (
        "Importa el export de recipe_type / recipe_type_size (BBDD nubu) en las "
        "tablas dish_type (DishCategory) y dish_type_size (DishCategorySize)."
    )

    def add_arguments(self, parser):
        parser.add_argument('recipe_type_sql', help='Ruta al fichero recipe_type.sql')
        parser.add_argument('recipe_type_size_sql', help='Ruta al fichero recipe_type_size.sql')
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Borra los datos existentes de dish_type/dish_type_size antes de importar.',
        )

    def handle(self, *args, **options):
        type_path = Path(options['recipe_type_sql'])
        size_path = Path(options['recipe_type_size_sql'])

        if not type_path.exists():
            raise CommandError(f"No existe el fichero {type_path}")
        if not size_path.exists():
            raise CommandError(f"No existe el fichero {size_path}")

        type_rows = parse_insert_tuples(type_path.read_text(encoding='utf-8'))
        size_rows = parse_insert_tuples(size_path.read_text(encoding='utf-8'))

        with transaction.atomic():
            if options['replace']:
                DishCategorySize.objects.all().delete()
                DishCategory.objects.all().delete()

            categories = {}
            for pk, group_name, name_es, name_en, name_de, name_el in type_rows:
                obj = DishCategory.objects.create(
                    id=int(pk),
                    group_name=group_name,
                    name_es=name_es,
                    name_en=name_en,
                    name_de=name_de,
                    name_el=name_el,
                )
                categories[obj.id] = obj

            created_sizes = 0
            for pk, quantity, size, category_id in size_rows:
                category_id = int(category_id)
                if category_id not in categories:
                    raise CommandError(
                        f"dish_type_size {pk} referencia dish_type {category_id}, "
                        "que no existe en recipe_type.sql"
                    )
                DishCategorySize.objects.create(
                    id=int(pk),
                    dish_category_id=category_id,
                    size=size,
                    quantity=quantity,
                )
                created_sizes += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importadas {len(categories)} categorías (dish_type) y {created_sizes} "
            "tamaños (dish_type_size)."
        ))
