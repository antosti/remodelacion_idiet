import random
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Dishes.models import Dish, DishCategory, DishCategorySize, DishProduct

from ._dish_category_rules import NAME_KEYWORD_RULES, classify_by_name, pick_size


class Command(BaseCommand):
    help = (
        "Segundo pase de clasificación: asigna dish_category (y dish_category_size) a partir "
        "de palabras clave en Dish.name, para categorías de preparación (pizza, bocadillos, "
        "sopas, postres...) que el ingrediente por sí solo no puede distinguir. Solo toca "
        "platos con dish_category aún nula. Por defecto es dry-run; usa --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                             help='Escribe los cambios en la base de datos.')
        parser.add_argument('--sample-size', type=int, default=8,
                             help='Nº de platos de ejemplo a mostrar por categoría (por defecto 8).')
        parser.add_argument('--seed', type=int, default=42, help='Semilla para el muestreo reproducible.')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        sample_size = options['sample_size']
        rng = random.Random(options['seed'])

        rule_category_ids = {cid for cid, _ in NAME_KEYWORD_RULES}
        existing = set(DishCategory.objects.filter(id__in=rule_category_ids).values_list('id', flat=True))
        missing = rule_category_ids - existing
        if missing:
            raise CommandError(f"Las categorías {sorted(missing)} del pase por nombre no existen en dish_type.")
        category_names = dict(
            DishCategory.objects.filter(id__in=rule_category_ids).values_list('id', 'name_es')
        )

        sizes_by_category = defaultdict(list)
        for cid, sid, qty in DishCategorySize.objects.filter(
            dish_category_id__in=rule_category_ids
        ).values_list('dish_category_id', 'id', 'quantity'):
            sizes_by_category[cid].append((sid, qty))
        for cid in sorted(rule_category_ids):
            if not sizes_by_category.get(cid):
                self.stdout.write(self.style.WARNING(
                    f"Aviso: dish_type {cid} ({category_names.get(cid)}) no tiene tamaños en dish_type_size."
                ))

        pending = list(Dish.objects.filter(dish_category__isnull=True).values_list('id', 'name'))
        rng.shuffle(pending)

        total_grams = defaultdict(int)
        for dish_id, quantity in DishProduct.objects.filter(
            dish__dish_category__isnull=True
        ).values_list('dish_id', 'quantity'):
            total_grams[dish_id] += quantity or 0

        matched = 0
        no_match = 0
        category_counts = Counter()
        examples_by_category = defaultdict(list)
        no_match_examples = []
        dish_category_result = {}
        dish_size_result = {}

        for dish_id, name in pending:
            category_id = classify_by_name(name)
            if category_id is None:
                no_match += 1
                if len(no_match_examples) < sample_size:
                    no_match_examples.append(name)
                continue

            matched += 1
            category_counts[category_id] += 1
            dish_category_result[dish_id] = category_id
            if len(examples_by_category[category_id]) < sample_size:
                examples_by_category[category_id].append(name)

            size_list = sizes_by_category.get(category_id) or []
            dish_size_result[dish_id] = pick_size(size_list, total_grams.get(dish_id, 0))

        w = self.stdout.write
        w("=== Clasificación de platos por nombre — MODO PRUEBA (usa --apply para escribir) ===")
        w("")
        w(f"Platos pendientes analizados (dish_category nula): {len(pending)}")
        pct = (matched / len(pending) * 100) if pending else 0
        w(f"  - CLASIFICADOS por nombre (se asignarán con --apply): {matched} ({pct:.1f} %)")
        w(f"  - Sin coincidencia de palabra clave: {no_match}")

        w("\n--- Detalle por categoría ---")
        for cid in sorted(rule_category_ids, key=lambda c: category_names.get(c, '')):
            count = category_counts.get(cid, 0)
            w(f"[{cid}] {category_names.get(cid)} — {count} platos")
            examples = examples_by_category.get(cid) or []
            if examples:
                w("    Ejemplos: " + ", ".join(f'"{e}"' for e in examples))

        w("\n--- Muestra de platos SIN coincidencia ---")
        for e in no_match_examples:
            w(f'  "{e}"')

        if not apply_changes:
            w(self.style.WARNING("\nMODO PRUEBA: no se ha escrito nada en la base de datos. Usa --apply para aplicar."))
            return

        updates = []
        for dish_id, category_id in dish_category_result.items():
            dish = Dish(id=dish_id)
            dish.dish_category_id = category_id
            dish.dish_category_size_id = dish_size_result.get(dish_id)
            updates.append(dish)

        with transaction.atomic():
            for i in range(0, len(updates), 1000):
                Dish.objects.bulk_update(
                    updates[i:i + 1000], ['dish_category_id', 'dish_category_size_id'], batch_size=1000
                )

        with_size = sum(1 for did in dish_category_result if dish_size_result.get(did))
        w(self.style.SUCCESS(
            f"\nAplicado: {len(updates)} platos con dish_category asignada por nombre "
            f"({with_size} también con dish_category_size)."
        ))
