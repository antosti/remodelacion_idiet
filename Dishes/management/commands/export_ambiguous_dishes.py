import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from Dishes.models import Dish, DishProduct

from ._dish_category_rules import AMBIGUOUS_GROUPS


class Command(BaseCommand):
    help = (
        "Exporta a CSV los platos sin dish_category cuyo ingrediente dominante pertenece a un "
        "grupo genuinamente ambiguo (carnes/aves/caza, o ensaladas/verduras): ni el ingrediente "
        "ni el nombre del plato distinguen la categoría exacta (corte de carne, o si es ensalada "
        "verde/no verde/verdura cocida), así que se deja para revisión manual. No escribe en la BBDD."
    )

    def add_arguments(self, parser):
        parser.add_argument('csv', type=Path, help='Ruta de salida del CSV.')

    def handle(self, *args, **options):
        csv_path = options['csv']

        pending_ids = set(Dish.objects.filter(dish_category__isnull=True).values_list('id', flat=True))
        dish_names = dict(
            Dish.objects.filter(id__in=pending_ids).values_list('id', 'name')
        )

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
        top_ingredient = {}  # dish_id -> (grams, name) del ingrediente que más pesa en el grupo ganador (aprox.)

        for dp_id, dish_id, quantity, food_group_id, product_name in dp_qs.values_list(
            'id', 'dish_id', 'quantity', 'product__food_group_id', 'product__food_name_spanish'
        ):
            quantity = quantity or 0
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

        rows = []
        for dish_id, group_grams in grams_by_dish_group.items():
            leader_key, leader_grams = max(group_grams.items(), key=lambda kv: kv[1])
            total = sum(group_grams.values())
            other_key = 'verduras' if leader_key == 'carnes' else 'carnes'
            mixto = 'si' if group_grams.get(other_key, 0) > 0 else 'no'
            top_grams, top_name = top_ingredient.get((dish_id, leader_key), (0, ''))
            cfg = AMBIGUOUS_GROUPS[leader_key]
            rows.append([
                dish_id,
                dish_names.get(dish_id, ''),
                cfg['label'],
                ','.join(str(c) for c in cfg['category_ids']),
                leader_grams,
                total,
                mixto,
                top_name,
                top_grams,
            ])

        rows.sort(key=lambda r: (r[2], -r[4]))

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'dish_id', 'dish_name', 'grupo_candidato', 'dish_category_ids_candidatos',
                'gramos_grupo_lider', 'gramos_totales_mapeados', 'mixto_carnes_y_verduras',
                'ingrediente_principal', 'gramos_ingrediente_principal',
            ])
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"Exportados {len(rows)} platos candidatos a revisión manual en {csv_path} "
            f"(de {len(pending_ids)} platos aún sin dish_category)."
        ))
