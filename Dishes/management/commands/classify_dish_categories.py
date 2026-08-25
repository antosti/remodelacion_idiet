import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Dishes.models import Dish, DishCategory, DishCategorySize, DishProduct

from ._dish_category_rules import (
    FOOD_GROUP_TO_CATEGORY,
    SUPER_GROUP_TO_CATEGORY,
    classify_dish,
    pick_size,
)

class Command(BaseCommand):
    help = (
        "Clasifica los Dish existentes en dish_category (y dish_category_size) a partir "
        "de los FoodGroup/SuperGroup de sus ingredientes. Por defecto solo genera un "
        "informe (dry-run); usa --apply para escribir los cambios en la base de datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Escribe los cambios en la base de datos. Sin esta opción solo se informa.',
        )
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Reclasifica también los platos que ya tienen dish_category asignada.',
        )
        parser.add_argument('--min-share', type=float, default=0.65,
                             help='Cuota mínima de gramos de la categoría líder (por defecto 0.65).')
        parser.add_argument('--min-mapped-grams', type=int, default=30,
                             help='Gramos mínimos mapeados para aceptar una clasificación (por defecto 30).')
        parser.add_argument('--sample-size', type=int, default=8,
                             help='Nº de platos de ejemplo a mostrar por categoría/motivo (por defecto 8).')
        parser.add_argument('--seed', type=int, default=42, help='Semilla para el muestreo reproducible.')
        parser.add_argument('--csv', type=Path, default=None, help='Ruta opcional para volcar el detalle por plato.')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        overwrite = options['overwrite']
        min_share = options['min_share']
        min_mapped_grams = options['min_mapped_grams']
        sample_size = options['sample_size']
        rng = random.Random(options['seed'])
        csv_path = options['csv']

        mapped_category_ids = set(FOOD_GROUP_TO_CATEGORY.values()) | set(SUPER_GROUP_TO_CATEGORY.values())
        existing_category_ids = set(
            DishCategory.objects.filter(id__in=mapped_category_ids).values_list('id', flat=True)
        )
        missing = mapped_category_ids - existing_category_ids
        if missing:
            raise CommandError(
                f"Las categorías {sorted(missing)} referenciadas en el mapeo no existen en dish_type."
            )
        category_names = dict(
            DishCategory.objects.filter(id__in=mapped_category_ids).values_list('id', 'name_es')
        )

        sizes_by_category = defaultdict(list)
        for cid, sid, qty in DishCategorySize.objects.filter(
            dish_category_id__in=mapped_category_ids
        ).values_list('dish_category_id', 'id', 'quantity'):
            sizes_by_category[cid].append((sid, qty))
        for cid in sorted(mapped_category_ids):
            if not sizes_by_category.get(cid):
                self.stdout.write(self.style.WARNING(
                    f"Aviso: dish_type {cid} ({category_names.get(cid)}) no tiene tamaños en dish_type_size."
                ))

        dish_qs = Dish.objects.all() if overwrite else Dish.objects.filter(dish_category__isnull=True)
        dish_names = dict(dish_qs.values_list('id', 'name'))
        already_classified = Dish.objects.filter(dish_category__isnull=False).count()

        dp_qs = DishProduct.objects.all() if overwrite else DishProduct.objects.filter(
            dish__dish_category__isnull=True
        )

        dp_supergroups = defaultdict(set)
        for dp_id, sg_id in dp_qs.values_list('id', 'product__super_groups__id'):
            if sg_id in SUPER_GROUP_TO_CATEGORY:
                dp_supergroups[dp_id].add(SUPER_GROUP_TO_CATEGORY[sg_id])

        total_grams = defaultdict(int)
        weighted_grams = defaultdict(lambda: defaultdict(int))
        conflicting_rows = 0

        for dp_id, dish_id, quantity, food_group_id in dp_qs.values_list(
            'id', 'dish_id', 'quantity', 'product__food_group_id'
        ):
            quantity = quantity or 0
            total_grams[dish_id] += quantity

            candidates = set(dp_supergroups.get(dp_id, ()))
            if food_group_id in FOOD_GROUP_TO_CATEGORY:
                candidates.add(FOOD_GROUP_TO_CATEGORY[food_group_id])

            if len(candidates) == 1:
                weighted_grams[dish_id][next(iter(candidates))] += quantity
            elif len(candidates) > 1:
                conflicting_rows += 1

        buckets = Counter()
        dish_category_result = {}
        dish_size_result = {}
        leader_shares = []
        category_counts = Counter()
        category_share_sum = defaultdict(float)
        examples_by_category = defaultdict(list)
        unclassified_examples = defaultdict(list)
        csv_rows = [] if csv_path else None

        dish_ids = list(dish_names.keys())
        rng.shuffle(dish_ids)

        for dish_id in dish_ids:
            grams_by_cat = weighted_grams.get(dish_id)
            status, category_id, share = classify_dish(grams_by_cat, min_share, min_mapped_grams)
            buckets[status] += 1
            dish_category_result[dish_id] = category_id
            size_id = None

            if status == 'matched':
                leader_shares.append(share)
                category_counts[category_id] += 1
                category_share_sum[category_id] += share
                if len(examples_by_category[category_id]) < sample_size:
                    examples_by_category[category_id].append(dish_names[dish_id])

                size_list = sizes_by_category.get(category_id) or []
                size_id = pick_size(size_list, total_grams.get(dish_id, 0))
                dish_size_result[dish_id] = size_id
            else:
                if len(unclassified_examples[status]) < sample_size:
                    unclassified_examples[status].append(dish_names[dish_id])

            if csv_rows is not None:
                mapped_grams = sum((grams_by_cat or {}).values())
                csv_rows.append([
                    dish_id, dish_names[dish_id], status,
                    category_id or '', category_names.get(category_id, ''),
                    total_grams.get(dish_id, 0), mapped_grams,
                    round(share, 4) if share is not None else '',
                    size_id or '',
                ])

        self._print_report(
            total_scope=len(dish_names), overwrite=overwrite, already_classified=already_classified,
            buckets=buckets, conflicting_rows=conflicting_rows, leader_shares=leader_shares,
            min_share=min_share, min_mapped_grams=min_mapped_grams, category_names=category_names,
            mapped_category_ids=mapped_category_ids, category_counts=category_counts,
            category_share_sum=category_share_sum, examples_by_category=examples_by_category,
            unclassified_examples=unclassified_examples,
        )

        if csv_path:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'dish_id', 'dish_name', 'resultado', 'dish_category_id', 'dish_category_name_es',
                    'total_grams_dish', 'mapped_grams', 'leader_share', 'dish_category_size_id',
                ])
                writer.writerows(csv_rows)
            self.stdout.write(f"Detalle por plato escrito en {csv_path}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nMODO PRUEBA: no se ha escrito nada en la base de datos. Usa --apply para aplicar."
            ))
            return

        matched_ids = [did for did, cid in dish_category_result.items() if cid is not None]
        updates = []
        for did in matched_ids:
            dish = Dish(id=did)
            dish.dish_category_id = dish_category_result[did]
            dish.dish_category_size_id = dish_size_result.get(did)
            updates.append(dish)

        with transaction.atomic():
            for i in range(0, len(updates), 1000):
                Dish.objects.bulk_update(
                    updates[i:i + 1000], ['dish_category_id', 'dish_category_size_id'], batch_size=1000
                )

        with_size = sum(1 for did in matched_ids if dish_size_result.get(did))
        self.stdout.write(self.style.SUCCESS(
            f"\nAplicado: {len(matched_ids)} platos con dish_category asignada "
            f"({with_size} de ellos también con dish_category_size)."
        ))

    def _print_report(self, *, total_scope, overwrite, already_classified, buckets, conflicting_rows,
                       leader_shares, min_share, min_mapped_grams, category_names, mapped_category_ids,
                       category_counts, category_share_sum, examples_by_category, unclassified_examples):
        w = self.stdout.write
        w("=== Clasificación de platos por dish_category — MODO PRUEBA (usa --apply para escribir) ===")
        w(f"Umbral --min-share={min_share}   Umbral --min-mapped-grams={min_mapped_grams}")
        w("")
        w(f"Total de platos analizados: {total_scope}")
        if not overwrite:
            w(f"  - Ya clasificados (omitidos; usa --overwrite): {already_classified}")
        w(f"  - Sin señal de ingredientes: {buckets.get('no_signal', 0)}")
        w(f"  - Señal débil (< {min_mapped_grams} g mapeados): {buckets.get('weak_signal', 0)}")
        w(f"  - Ambigua (líder < {min_share:.0%} de los gramos mapeados): {buckets.get('ambiguous', 0)}")
        matched = buckets.get('matched', 0)
        pct = (matched / total_scope * 100) if total_scope else 0
        w(f"  - CLASIFICADOS (se asignarán con --apply): {matched} ({pct:.1f} %)")
        w(f"  - Filas dish_product con etiquetado contradictorio (ignoradas): {conflicting_rows}")

        if leader_shares:
            buckets_hist = Counter()
            for s in leader_shares:
                if s < 0.65:
                    buckets_hist['50-65%'] += 1
                elif s < 0.80:
                    buckets_hist['65-80%'] += 1
                elif s < 0.95:
                    buckets_hist['80-95%'] += 1
                else:
                    buckets_hist['95-100%'] += 1
            w("\n--- Distribución de leader_share entre los clasificados ---")
            for label in ['50-65%', '65-80%', '80-95%', '95-100%']:
                w(f"  {label}: {buckets_hist.get(label, 0)}")

        w("\n--- Detalle por categoría (las 13 con regla) ---")
        for cid in sorted(mapped_category_ids, key=lambda c: category_names.get(c, '')):
            count = category_counts.get(cid, 0)
            avg_share = (category_share_sum[cid] / count) if count else 0
            w(f"[{cid}] {category_names.get(cid)} — {count} platos · share medio {avg_share:.1%}")
            examples = examples_by_category.get(cid) or []
            if examples:
                w("    Ejemplos: " + ", ".join(f'"{e}"' for e in examples))

        w("\n--- Muestra de platos NO clasificados ---")
        for status in ['ambiguous', 'weak_signal', 'no_signal']:
            examples = unclassified_examples.get(status) or []
            for e in examples:
                w(f"  [{status}] \"{e}\"")
