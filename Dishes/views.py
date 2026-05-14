from django.shortcuts import render, redirect
from decimal import Decimal
from operator import itemgetter

from Intakes.models import Intake
from Dishes.models import Dish
from Micronutrients.models import Micronutrient
from Products.models import Product
from idiet.views import paginate_queryset


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


def create_dish(request):
    intakes = Intake.objects.all().order_by('order')
    micronutrient_sections = get_micronutrient_sections()

    if request.method == 'POST':
        Dish.objects.create(
            name=request.POST.get('recipe_name'),
            recipe_elaboration=request.POST.get('description'),
            language='es',
        )

        return redirect('create_dish')

    return render(request, 'admin/create_dish.html', {
        'intakes': intakes,
        'micronutrient_sections': micronutrient_sections,
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


def list_active_dishes(request):
    context = get_dish_context(request, active=True)
    return render(request, 'admin/list_active_dishes.html', context)


def list_deactive_dishes(request):
    context = get_dish_context(request, active=False)
    return render(request, 'admin/list_deactive_dishes.html', context)