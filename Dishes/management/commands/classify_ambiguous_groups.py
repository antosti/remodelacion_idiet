import random
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Dishes.models import Dish, DishCategory, DishCategorySize, DishProduct

from ._dish_category_rules import (
    AMBIGUOUS_GROUPS,
    ENSALADA_PATTERN,
    classify_meat_by_product_name,
    classify_veg_group,
    pick_size,
)

ALL_TARGET_CATEGORY_IDS = {cid for cfg in AMBIGUOUS_GROUPS.values() for cid in cfg['category_ids']}

# Un plato con "ensalada" en el nombre pero con más gramos de carne que de
# verdura (ej. "Ensalada de pollo") sigue siendo una ensalada: el nombre manda.
# Fuera de ese caso, solo se acepta "Verduras cocidas" (6) cuando el grupo
# verduras domina claramente sobre cualquier carne presente en el mismo plato
# (ej. "Muslo de pollo a la plancha con calabaza" NO debe convertirse en un
# plato de verdura solo porque la calabaza pesa más que el muslo).
MIN_VEG_SHARE = 0.65

# Guarda adicional: el ingrediente líder del grupo (carne o verdura) debe ser
# también el ingrediente individual más pesado de TODO el plato (no solo
# dentro del grupo rastreado). Sin esto, "Arroz tres delicias" (60g de arroz,
# 30g de jamón cocinado, arroz no rastreado) se clasificaba como "carne" solo
# por ser el único ingrediente del grupo, aunque el arroz pesa más y es el
# verdadero protagonista del plato. No se aplica a las ensaladas: ahí el
# nombre ya confirma que es una ensalada independientemente de qué ingrediente
# pese más.


class Command(BaseCommand):
    help = (
        "Tercer pase: resuelve los grupos ambiguos 'carnes' (18/19/20/21/22, por nombre del "
        "ingrediente dominante) y 'verduras' (4/5/6, por nombre del plato + ingrediente dominante) "
        "para los platos que el export_ambiguous_dishes dejó pendientes. Por defecto es dry-run; "
        "usa --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Escribe los cambios en la base de datos.')
        parser.add_argument('--sample-size', type=int, default=8,
                             help='Nº de platos de ejemplo a mostrar por categoría (por defecto 8).')
        parser.add_argument('--seed', type=int, default=42, help='Semilla para el muestreo reproducible.')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        sample_size = options['sample_size']
        rng = random.Random(options['seed'])

        existing = set(DishCategory.objects.filter(id__in=ALL_TARGET_CATEGORY_IDS).values_list('id', flat=True))
        missing = ALL_TARGET_CATEGORY_IDS - existing
        if missing:
            raise CommandError(f"Las categorías {sorted(missing)} no existen en dish_type.")
        category_names = dict(
            DishCategory.objects.filter(id__in=ALL_TARGET_CATEGORY_IDS).values_list('id', 'name_es')
        )

        sizes_by_category = defaultdict(list)
        for cid, sid, qty in DishCategorySize.objects.filter(
            dish_category_id__in=ALL_TARGET_CATEGORY_IDS
        ).values_list('dish_category_id', 'id', 'quantity'):
            sizes_by_category[cid].append((sid, qty))

        pending_ids = list(Dish.objects.filter(dish_category__isnull=True).values_list('id', flat=True))
        dish_names = dict(Dish.objects.filter(id__in=pending_ids).values_list('id', 'name'))

        group_food_groups = {}
        group_super_groups = {}
        for key, cfg in AMBIGUOUS_GROUPS.items():
            for fg in cfg['food_groups']:
                group_food_groups[fg] = key
            for sg in cfg['super_groups']:
                group_super_groups[sg] = key

        dp_qs = DishProduct.objects.filter(dish_id__in=pending_ids)

        dp_groups = defaultdict(set)
        for dp_id, sg_id in dp_qs.values_list('id', 'product__super_groups__id'):
            if sg_id in group_super_groups:
                dp_groups[dp_id].add(group_super_groups[sg_id])

        grams_by_dish_group = defaultdict(lambda: defaultdict(int))
        top_ingredient = {}  # (dish_id, group_key) -> (grams, product_name)
        total_grams = defaultdict(int)
        heaviest_overall = {}  # dish_id -> grams del ingrediente individual más pesado del plato (cualquier grupo)

        for dp_id, dish_id, quantity, food_group_id, product_name in dp_qs.values_list(
            'id', 'dish_id', 'quantity', 'product__food_group_id', 'product__food_name_spanish'
        ):
            quantity = quantity or 0
            total_grams[dish_id] += quantity
            if quantity > heaviest_overall.get(dish_id, -1):
                heaviest_overall[dish_id] = quantity

            candidates = set(dp_groups.get(dp_id, ()))
            if food_group_id in group_food_groups:
                candidates.add(group_food_groups[food_group_id])
            if len(candidates) != 1:
                continue
            group_key = next(iter(candidates))
            grams_by_dish_group[dish_id][group_key] += quantity

            current = top_ingredient.get((dish_id, group_key))
            if current is None or quantity > current[0]:
                top_ingredient[(dish_id, group_key)] = (quantity, product_name)

        category_counts = Counter()
        examples_by_category = defaultdict(list)
        dish_category_result = {}
        dish_size_result = {}
        no_rule_match = 0
        no_group_signal = 0

        dish_ids = list(grams_by_dish_group.keys())
        rng.shuffle(dish_ids)

        for dish_id in dish_ids:
            group_grams = grams_by_dish_group[dish_id]
            name = dish_names.get(dish_id, '')
            carnes_g = group_grams.get('carnes', 0)
            veg_g = group_grams.get('verduras', 0)

            if ENSALADA_PATTERN.search(name):
                # El nombre manda: sigue siendo una ensalada aunque la carne pese más
                # (ej. "Ensalada de pollo"). Se usa el ingrediente vegetal dominante,
                # si lo hay, para decidir verde/no verde.
                _, top_name = top_ingredient.get((dish_id, 'verduras'), (0, ''))
                category_id = classify_veg_group(name, top_name)
            else:
                leader_key, leader_grams = max(group_grams.items(), key=lambda kv: kv[1])
                _, top_name = top_ingredient.get((dish_id, leader_key), (0, ''))

                if leader_grams < heaviest_overall.get(dish_id, 0):
                    # El ingrediente líder del grupo no es el ingrediente más pesado del
                    # plato completo (ej. el arroz, sin rastrear, pesa más que el jamón):
                    # no es realmente un plato de carne/verdura, queda para revisión manual.
                    category_id = None
                elif leader_key == 'carnes':
                    category_id = classify_meat_by_product_name(top_name)
                else:
                    total = carnes_g + veg_g
                    veg_share = (veg_g / total) if total else 1.0
                    if veg_share < MIN_VEG_SHARE:
                        # Plato mixto carne+verdura donde ninguna de las dos domina
                        # con claridad: no forzamos categoría, queda para revisión manual.
                        category_id = None
                    else:
                        category_id = classify_veg_group(name, top_name)

            if category_id is None:
                no_rule_match += 1
                continue

            category_counts[category_id] += 1
            dish_category_result[dish_id] = category_id
            if len(examples_by_category[category_id]) < sample_size:
                examples_by_category[category_id].append(f'{name}  [{top_name}]')

            size_list = sizes_by_category.get(category_id) or []
            dish_size_result[dish_id] = pick_size(size_list, total_grams.get(dish_id, 0))

        no_group_signal = len(pending_ids) - len(grams_by_dish_group)

        w = self.stdout.write
        w("=== Clasificación de grupos ambiguos (carnes / verduras) — MODO PRUEBA ===")
        w("")
        w(f"Platos pendientes (dish_category nula): {len(pending_ids)}")
        w(f"  - Sin ningún ingrediente del grupo carnes/verduras: {no_group_signal}")
        w(f"  - Con ingrediente del grupo, pero sin regla de nombre aplicable: {no_rule_match}")
        matched = sum(category_counts.values())
        w(f"  - CLASIFICADOS (se asignarán con --apply): {matched}")

        w("\n--- Detalle por categoría ---")
        for cid in sorted(ALL_TARGET_CATEGORY_IDS, key=lambda c: category_names.get(c, '')):
            count = category_counts.get(cid, 0)
            w(f"[{cid}] {category_names.get(cid)} — {count} platos")
            examples = examples_by_category.get(cid) or []
            if examples:
                w("    Ejemplos: " + " | ".join(examples))

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
            f"\nAplicado: {len(updates)} platos con dish_category asignada ({with_size} también con dish_category_size)."
        ))
