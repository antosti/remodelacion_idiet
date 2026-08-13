from django.db.models import Q

from Dishes.models import Dish
from Dishes.views import calculate_dish_nutrition
from FoodGroup.models import FoodGroupExcluded
from idiet.permissions import is_admin_user
from Products.models import ProductExcluded
from Menus.generator.domain import DishCandidate

ROLE_TO_DISH_TYPES = {
    'single': [Dish.DishType.MAIN, Dish.DishType.SINGLE],
    'starter': [Dish.DishType.STARTER],
    'main': [Dish.DishType.MAIN, Dish.DishType.SINGLE],
    'dessert': [Dish.DishType.DESSERT],
}


def _to_candidate(dish):
    nutrition = calculate_dish_nutrition(dish)
    return DishCandidate(
        dish_id=dish.id,
        name=dish.name,
        kcal_100g=float(nutrition['kcal_100g']),
        prot_100g=float(nutrition['protein_100g']),
        fat_100g=float(nutrition['fat_100g']),
        carb_100g=float(nutrition['carbs_100g']),
    )


def build_candidate_pools(client, user, meal_slots):
    """dict[slot.key][role] -> list[DishCandidate], solo para los roles activos de cada slot.

    Los platos se limitan a los del propio `user` mas los globales (sin
    propietario), salvo que `user` sea staff/superuser, en cuyo caso se ven
    todos (mismo criterio de aislamiento que Clients/Appointments)."""
    excluded_products = set(
        ProductExcluded.objects.filter(client=client).values_list('product_id', flat=True)
    )
    excluded_groups = set(
        FoodGroupExcluded.objects.filter(client=client).values_list('food_group_id', flat=True)
    )
    restrict_by_owner = not is_admin_user(user)

    def pool_for(intake, role):
        qs = Dish.objects.filter(active=True, dish_type__in=ROLE_TO_DISH_TYPES[role])
        qs = qs.filter(Q(intakes__isnull=True) | Q(intakes=intake)).distinct()
        if restrict_by_owner:
            qs = qs.filter(Q(user__isnull=True) | Q(user=user))
        qs = qs.prefetch_related('dishproduct_set__product')

        if excluded_products:
            qs = qs.exclude(product__id__in=excluded_products)
        if excluded_groups:
            qs = qs.exclude(product__food_group_id__in=excluded_groups)

        return [_to_candidate(dish) for dish in qs]

    pools = {}
    for slot in meal_slots:
        pools[slot.key] = {
            role: pool_for(slot.intakes[role], role)
            for role in slot.active_roles()
        }
    return pools
