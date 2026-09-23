from collections import defaultdict

from django.db.models import Q

from Dishes.models import Dish, DishCategorySize
from Dishes.views import calculate_dish_nutrition
from FoodGroup.models import FoodGroupExcluded
from idiet.permissions import is_admin_user
from Products.models import Product, ProductExcluded, ProductMicronutrient
from Menus.generator.domain import DishCandidate
from Menus.generator.micronutrients import MICRO_IDS

ROLE_TO_DISH_TYPES = {
    'single': [Dish.DishType.MAIN, Dish.DishType.SINGLE],
    'starter': [Dish.DishType.STARTER],
    'main': [Dish.DishType.MAIN, Dish.DishType.SINGLE],
    'dessert': [Dish.DishType.DESSERT],
}

# Indicacion explicita de la nutricionista de excluir el huevo del calculo
# de colesterol: el limite de Menus.generator.micronutrients no debe contar
# el colesterol que aporta el huevo, ni como producto suelto (FoodGroup
# "Huevos") ni como ingrediente de un plato/preparado que lo lleve (SuperGroup
# "HUEVOS", que ademas cubre productos como mayonesa, quiche o tortilla de
# patata cuyo colesterol viene del huevo aunque el producto ya no lo sea).
EGG_FOOD_GROUP_ID = 44
EGG_SUPER_GROUP_ID = 5
COLESTEROL_MICRO_ID = MICRO_IDS['colesterol']


def _product_micro_map(product_ids):
    """dict[product_id][micronutrient_id] -> value (por 100g de producto).
    Descarta el colesterol de los productos con huevo (ver EGG_FOOD_GROUP_ID
    / EGG_SUPER_GROUP_ID); el resto de sus micronutrientes se cuenta normal."""
    egg_product_ids = set(
        Product.objects.filter(id__in=product_ids)
        .filter(Q(food_group_id=EGG_FOOD_GROUP_ID) | Q(super_groups__id=EGG_SUPER_GROUP_ID))
        .distinct()
        .values_list('id', flat=True)
    )
    product_micro_map = defaultdict(dict)
    for pm in ProductMicronutrient.objects.filter(
        product_id__in=product_ids, micronutrient_id__in=MICRO_IDS.values()
    ):
        if pm.micronutrient_id == COLESTEROL_MICRO_ID and pm.product_id in egg_product_ids:
            continue
        product_micro_map[pm.product_id][pm.micronutrient_id] = pm.value
    return product_micro_map


def _dish_micros_100g(dish, product_micro_map):
    """Mismo patron que calculate_dish_nutrition (Dishes/views.py) pero
    agregando micronutrientes de ProductMicronutrient en vez de macros."""
    total_quantity = 0
    totals = defaultdict(float)

    for dish_product in dish.dishproduct_set.all():
        quantity = dish_product.quantity or 0
        total_quantity += quantity
        for micro_id, value in product_micro_map.get(dish_product.product_id, {}).items():
            totals[micro_id] += float(value) * quantity / 100

    if total_quantity == 0:
        return {}

    return {micro_id: value / total_quantity * 100 for micro_id, value in totals.items()}


def _to_candidate(dish, portion_grams, product_micro_map=None):
    nutrition = calculate_dish_nutrition(dish)

    if product_micro_map is None:
        product_ids = [dp.product_id for dp in dish.dishproduct_set.all()]
        product_micro_map = _product_micro_map(product_ids)

    return DishCandidate(
        dish_id=dish.id,
        name=dish.name,
        kcal_100g=float(nutrition['kcal_100g']),
        prot_100g=float(nutrition['protein_100g']),
        fat_100g=float(nutrition['fat_100g']),
        carb_100g=float(nutrition['carbs_100g']),
        portion_grams=portion_grams,
        micros_100g=_dish_micros_100g(dish, product_micro_map),
    )


def build_candidate_pools(client, user, meal_slots, portion_size=None):
    """dict[slot.key][role] -> list[DishCandidate], solo para los roles activos de cada slot.

    Los platos se limitan a los del propio `user` mas los globales (sin
    propietario), salvo que `user` sea staff/superuser, en cuyo caso se ven
    todos (mismo criterio de aislamiento que Clients/Appointments).

    `portion_size` (uno de DishCategorySize.Size, ej. 'S') fuerza la racion de
    TODOS los platos a lo que mide ese tamano en la categoria propia de cada
    plato, en vez de dejar que cada uno use su tamano natural."""
    excluded_products = set(
        ProductExcluded.objects.filter(client=client).values_list('product_id', flat=True)
    )
    excluded_groups = set(
        FoodGroupExcluded.objects.filter(client=client).values_list('food_group_id', flat=True)
    )
    restrict_by_owner = not is_admin_user(user)

    # Gramos del tamano elegido por categoria (ej. {carnes: 180, postres: 90}),
    # y una media general de ese mismo tamano para platos sin categoria o cuya
    # categoria no tiene ese tamano definido.
    quantity_by_category = {}
    fallback_for_size = None
    if portion_size:
        quantity_by_category = {
            category_id: float(quantity)
            for category_id, quantity in DishCategorySize.objects.filter(
                size=portion_size
            ).values_list('dish_category_id', 'quantity')
        }
        if quantity_by_category:
            values = quantity_by_category.values()
            fallback_for_size = sum(values) / len(values)

    def resolve_portion(dish, fallback_intake_portion_grams):
        if portion_size:
            return quantity_by_category.get(dish.dish_category_id, fallback_for_size)
        if dish.dish_category_size:
            return float(dish.dish_category_size.quantity)
        return fallback_intake_portion_grams

    def pool_for(intake, role):
        qs = Dish.objects.filter(active=True, dish_type__in=ROLE_TO_DISH_TYPES[role])
        qs = qs.filter(Q(intakes__isnull=True) | Q(intakes=intake)).distinct()
        if restrict_by_owner:
            qs = qs.filter(Q(user__isnull=True) | Q(user=user))
        qs = qs.select_related('dish_category_size').prefetch_related('dishproduct_set__product')

        if excluded_products:
            qs = qs.exclude(product__id__in=excluded_products)
        if excluded_groups:
            qs = qs.exclude(product__food_group_id__in=excluded_groups)

        dishes = list(qs)

        # Ingesta a la que pertenece este slot (desayuno, comida...): tamano
        # de reserva para los platos sin dish_category_size propio, sacado de
        # la media de los que si lo tienen dentro de esta misma ingesta.
        known_sizes = [float(d.dish_category_size.quantity) for d in dishes if d.dish_category_size]
        fallback_portion_grams = sum(known_sizes) / len(known_sizes) if known_sizes else None

        product_ids = {
            dish_product.product_id
            for dish in dishes
            for dish_product in dish.dishproduct_set.all()
        }
        product_micro_map = _product_micro_map(product_ids)

        return [
            _to_candidate(dish, resolve_portion(dish, fallback_portion_grams), product_micro_map)
            for dish in dishes
        ]

    pools = {}
    for slot in meal_slots:
        pools[slot.key] = {
            role: pool_for(slot.intakes[role], role)
            for role in slot.active_roles()
        }
    return pools
