from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from decimal import Decimal
from operator import itemgetter

from Intakes.models import Intake
from Dishes.models import Dish, DishProduct
from Micronutrients.models import Micronutrient
from Products.models import Product
from idiet.views import paginate_queryset
from django.contrib.auth.decorators import login_required


def get_dish_ingredient_pairs(request):
    product_ids = request.POST.getlist('ingredient_product_id')
    quantities = request.POST.getlist('ingredient_quantity')

    pairs = []

    for product_id, quantity in zip(product_ids, quantities):
        if not product_id:
            continue

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue

        if quantity <= 0:
            continue

        pairs.append((product_id, quantity))

    if not pairs:
        return []

    valid_product_ids = set(
        Product.objects.filter(
            id__in=[product_id for product_id, _ in pairs],
            is_active=True,
        ).values_list('id', flat=True)
    )

    return [
        (product_id, quantity)
        for product_id, quantity in pairs
        if int(product_id) in valid_product_ids
    ]


MICRONUTRIENT_SECTIONS = [
    {
        'title': 'General',
        'ids': [1, 69, 2, 70, 71, 4, 5, 6, 7],
    },
    {
        'title': 'Vitaminas y otros',
        'ids': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 72, 23],
    },
    {
        'title': 'Minerales',
        'ids': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38],
    },
    {
        'title': 'Ácidos grasos',
        'ids': list(range(39, 69)),
    },
]


MICRONUTRIENTS_IN_GRAMS = {1, 2, 4, 5, 6, 68, 69, 70, 71}
MICRONUTRIENTS_IN_UG = {8, 15, 16, 17, 19, 22, 32, 33, 37, 38, 72}


def get_micronutrient_unit(micronutrient_id):
    if micronutrient_id in MICRONUTRIENTS_IN_GRAMS:
        return 'g'

    if micronutrient_id in MICRONUTRIENTS_IN_UG:
        return 'ug'

    return 'mg'


def get_micronutrient_sections():
    all_ids = []

    for section in MICRONUTRIENT_SECTIONS:
        all_ids += section['ids']

    micronutrients = Micronutrient.objects.filter(id__in=all_ids)
    micronutrients_by_id = {micronutrient.id: micronutrient for micronutrient in micronutrients}

    sections = []

    for section in MICRONUTRIENT_SECTIONS:
        section_micronutrients = []

        for micronutrient_id in section['ids']:
            micronutrient = micronutrients_by_id.get(micronutrient_id)

            if micronutrient:
                micronutrient.unit = get_micronutrient_unit(micronutrient.id)
                section_micronutrients.append(micronutrient)

        sections.append({
            'title': section['title'],
            'micronutrients': section_micronutrients,
        })

    return sections

@login_required
def create_dish(request):
    intakes = Intake.objects.all().order_by('order')
    micronutrient_sections = get_micronutrient_sections()

    if request.method == 'POST':
        ingredient_pairs = get_dish_ingredient_pairs(request)

        with transaction.atomic():
            dish = Dish.objects.create(
                name=request.POST.get('recipe_name'),
                recipe_elaboration=request.POST.get('description'),
                language='es',
                dish_type=request.POST.get('dish_type') or Dish.DishType.MAIN,
                user=request.user,
            )

            dish.intakes.set(request.POST.getlist('intakes'))

            for product_id, quantity in ingredient_pairs:
                DishProduct.objects.create(dish=dish, product_id=product_id, quantity=quantity)

        return redirect('create_dish')

    return render(request, 'admin/create_dish.html', {
        'intakes': intakes,
        'micronutrient_sections': micronutrient_sections,
        'dish_type_choices': Dish.DishType.choices,
    })


def calculate_dish_nutrition(dish):
    total_quantity = Decimal('0')

    total_kcal = Decimal('0')
    total_carbs = Decimal('0')
    total_protein = Decimal('0')
    total_fat = Decimal('0')

    dish_products = dish.dishproduct_set.all()

    for dish_product in dish_products:
        product = dish_product.product
        quantity = dish_product.quantity or Decimal('0')

        total_quantity += quantity

        total_kcal += (product.kcal_100g or Decimal('0')) * quantity / Decimal('100')
        total_carbs += (product.ch_g or Decimal('0')) * quantity / Decimal('100')
        total_protein += (product.prot_g or Decimal('0')) * quantity / Decimal('100')
        total_fat += (product.fat_g or Decimal('0')) * quantity / Decimal('100')

    if total_quantity == 0:
        return {
            'kcal_100g': 0,
            'carbs_100g': 0,
            'protein_100g': 0,
            'fat_100g': 0,
        }

    return {
        'kcal_100g': round(total_kcal / total_quantity * 100, 2),
        'carbs_100g': round(total_carbs / total_quantity * 100, 2),
        'protein_100g': round(total_protein / total_quantity * 100, 2),
        'fat_100g': round(total_fat / total_quantity * 100, 2),
    }


def get_dish_origin(dish):
    origins = []

    for dish_product in dish.dishproduct_set.all():
        origin = dish_product.product.origin_db or 'i-Diet'

        if origin not in origins:
            origins.append(origin)

    if not origins:
        return 'Sin origen'

    if len(origins) == 1:
        return origins[0]

    return 'Mixto'


def dish_has_origin(dish, origin_filter):
    for dish_product in dish.dishproduct_set.all():
        origin = dish_product.product.origin_db or 'i-Diet'

        if origin == origin_filter:
            return True

    return False


def get_dish_context(request, active=True):
    intakes = Intake.objects.all().order_by('order')

    origin_options = Product.objects.exclude(
        origin_db__isnull=True
    ).exclude(
        origin_db=''
    ).values_list(
        'origin_db', flat=True
    ).distinct().order_by('origin_db')

    dish_name = request.GET.get('dish_name', '').strip()
    origin_filter = request.GET.get('origin_filter', '').strip()
    intake_filter = request.GET.get('intake_filter', '').strip()

    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    dishes = Dish.objects.filter(active=active).prefetch_related(
        'dishproduct_set__product'
    )

    if dish_name:
        dishes = dishes.filter(name__icontains=dish_name)

    dish_list = []

    for dish in dishes:
        if origin_filter and not dish_has_origin(dish, origin_filter):
            continue

        nutrition = calculate_dish_nutrition(dish)

        dish_list.append({
            'id': dish.id,
            'name': dish.name,
            'kcal_100g': nutrition['kcal_100g'],
            'carbs_100g': nutrition['carbs_100g'],
            'protein_100g': nutrition['protein_100g'],
            'fat_100g': nutrition['fat_100g'],
            'origin': get_dish_origin(dish),
        })

    allowed_sorts = {
        'name': 'name',
        'kcal': 'kcal_100g',
        'carbs': 'carbs_100g',
        'protein': 'protein_100g',
        'fat': 'fat_100g',
        'origin': 'origin',
    }

    current_sort = sort if sort in allowed_sorts else 'name'
    current_direction = 'desc' if direction == 'desc' else 'asc'

    dish_list = sorted(dish_list, key=itemgetter(allowed_sorts[current_sort]))

    if current_direction == 'desc':
        dish_list.reverse()

    pagination = paginate_queryset(request, dish_list)

    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    return {
        'intakes': intakes,
        'origin_options': origin_options,
        'dish_list': pagination['page_obj'],
        'dish_name': dish_name,
        'origin_filter': origin_filter,
        'intake_filter': intake_filter,
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
    }

@login_required
def list_active_dishes(request):
    context = get_dish_context(request, active=True)
    return render(request, 'admin/list_active_dishes.html', context)


@login_required
def list_deactive_dishes(request):
    context = get_dish_context(request, active=False)
    return render(request, 'admin/list_deactive_dishes.html', context)


@login_required
def edit_dish(request, id):
    dish = get_object_or_404(Dish, id=id, active=True)

    if request.method == 'POST':
        ingredient_pairs = get_dish_ingredient_pairs(request)

        with transaction.atomic():
            dish.name = request.POST.get('recipe_name')
            dish.recipe_elaboration = request.POST.get('description')
            dish.dish_type = request.POST.get('dish_type') or Dish.DishType.MAIN
            dish.save()
            dish.intakes.set(request.POST.getlist('intakes'))

            dish.dishproduct_set.all().delete()

            for product_id, quantity in ingredient_pairs:
                DishProduct.objects.create(dish=dish, product_id=product_id, quantity=quantity)

        messages.success(request, 'La receta se ha actualizado correctamente.')
        return redirect('list_active_dishes')

    intakes = Intake.objects.all().order_by('order')
    dish_intake_ids = set(dish.intakes.values_list('id', flat=True))
    micronutrient_sections = get_micronutrient_sections()
    nutrition = calculate_dish_nutrition(dish)
    dish_products = dish.dishproduct_set.select_related('product').all()

    existing_ingredients = [
        {
            'id': dish_product.product.id,
            'name': dish_product.product.food_name_spanish,
            'kcal_100g': float(dish_product.product.kcal_100g),
            'ch_g': float(dish_product.product.ch_g),
            'prot_g': float(dish_product.product.prot_g),
            'fat_g': float(dish_product.product.fat_g),
            'quantity': dish_product.quantity,
        }
        for dish_product in dish_products
    ]

    return render(request, 'admin/edit_dish.html', {
        'dish': dish,
        'intakes': intakes,
        'dish_intake_ids': dish_intake_ids,
        'micronutrient_sections': micronutrient_sections,
        'nutrition': nutrition,
        'dish_products': dish_products,
        'existing_ingredients': existing_ingredients,
        'dish_type_choices': Dish.DishType.choices,
    })


@login_required
@require_POST
def deactivate_dish(request, id):
    dish = get_object_or_404(Dish, id=id, active=True)
    dish.active = False
    dish.save(update_fields=['active'])
    messages.success(request, 'La receta se ha desactivado correctamente.')
    return redirect('list_active_dishes')


@login_required
@require_POST
def reactivate_dish(request, id):
    dish = get_object_or_404(Dish, id=id, active=False)
    dish.active = True
    dish.save(update_fields=['active'])
    messages.success(request, 'La receta se ha reactivado correctamente.')
    return redirect('list_deactive_dishes')


@login_required
@require_POST
def delete_dish(request, id):
    dish = get_object_or_404(Dish, id=id, active=False)
    dish.delete()
    messages.success(request, 'La receta se ha eliminado definitivamente.')
    return redirect('list_deactive_dishes')