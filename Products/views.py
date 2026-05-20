from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import render, redirect

from FoodGroup.models import FoodGroup
from Micronutrients.models import Micronutrient
from Products.models import Product, ProductMicronutrient
from SuperGroup.models import SuperGroup
from idiet.views import paginate_queryset


FOOD_MICRONUTRIENT_SECTIONS = [
    {
        'title': 'General',
        'ids': [3, 1, 2, 4, 5, 6, 7],
    },
    {
        'title': 'Vitaminas y otros',
        'ids': list(range(8, 24)) + [72],
    },
    {
        'title': 'Minerales',
        'ids': list(range(24, 39)),
    },
    {
        'title': 'Ácidos grasos',
        'ids': list(range(39, 69)),
    },
]


MICRONUTRIENTS_IN_GRAMS = {1, 2, 4, 5, 6, 68}
MICRONUTRIENTS_IN_UG = {8, 15, 16, 17, 19, 22, 32, 33, 37, 38}


def get_micronutrient_unit(micronutrient_id):
    if micronutrient_id in MICRONUTRIENTS_IN_GRAMS:
        return 'g'

    if micronutrient_id in MICRONUTRIENTS_IN_UG:
        return 'ug'

    if micronutrient_id == 3:
        return '%'

    return 'mg'


def get_food_micronutrient_sections():
    all_ids = []

    for section in FOOD_MICRONUTRIENT_SECTIONS:
        all_ids += section['ids']

    micronutrients = Micronutrient.objects.filter(id__in=all_ids)

    micronutrients_by_id = {
        micronutrient.id: micronutrient
        for micronutrient in micronutrients
    }

    sections = []

    for section in FOOD_MICRONUTRIENT_SECTIONS:
        section_micronutrients = []

        for micronutrient_id in section['ids']:
            micronutrient = micronutrients_by_id.get(micronutrient_id)

            if not micronutrient:
                continue

            micronutrient.unit = get_micronutrient_unit(micronutrient.id)
            micronutrient.input_name = f'micronutrient_{micronutrient.id}'

            section_micronutrients.append(micronutrient)

        sections.append({
            'title': section['title'],
            'micronutrients': section_micronutrients,
        })

    return sections


def get_decimal_value(request, field_name):
    raw_value = request.POST.get(field_name, '').strip()

    if raw_value == '':
        return Decimal('0.00')

    try:
        return Decimal(raw_value)
    except InvalidOperation:
        return Decimal('0.00')


def create_food(request):
    food_groups = FoodGroup.objects.all()
    super_groups = SuperGroup.objects.all()
    micronutrient_sections = get_food_micronutrient_sections()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        english_name = request.POST.get('english_name', '').strip()
        super_group_ids = request.POST.getlist('super_group')

        with transaction.atomic():
            product = Product.objects.create(
                food_name=name,
                food_name_spanish=name,
                food_name_eng=english_name or name,
                origin_db='Act. i-Diet',
                ed_porc=100,
                kcal_100g=get_decimal_value(request, 'kcal_100g'),
                prot_g=get_decimal_value(request, 'proteins'),
                ch_g=get_decimal_value(request, 'hydrates'),
                fat_g=get_decimal_value(request, 'fats'),
                food_group_id=request.POST.get('food_group') or None,
            )

            if super_group_ids:
                product.super_groups.set(super_group_ids)

            product_micronutrients = []

            for section in micronutrient_sections:
                for micronutrient in section['micronutrients']:
                    value = get_decimal_value(request, micronutrient.input_name)

                    if value == Decimal('0.00'):
                        continue

                    product_micronutrients.append(
                        ProductMicronutrient(
                            product=product,
                            micronutrient=micronutrient,
                            value=value,
                        )
                    )

            ProductMicronutrient.objects.bulk_create(product_micronutrients)

        return redirect('create_food')

    return render(request, 'admin/create_food.html', {
        'food_groups': food_groups,
        'super_groups': super_groups,
        'micronutrient_sections': micronutrient_sections,
    })


def get_foods_list_context(request, products):
    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    allowed_sorts = {
        'name': 'food_name_spanish',
        'group': 'food_group__name',
        'kcal': 'kcal_100g',
        'carbs': 'ch_g',
        'protein': 'prot_g',
        'fat': 'fat_g',
        'origin': 'origin_db',
    }

    current_sort = sort if sort in allowed_sorts else 'name'
    current_direction = 'desc' if direction == 'desc' else 'asc'

    order_field = allowed_sorts[current_sort]

    if current_direction == 'desc':
        order_field = f'-{order_field}'

    products = products.order_by(order_field)

    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    pagination = paginate_queryset(request, products)

    return {
        'products': pagination['page_obj'],
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
    }


def list_active_foods(request):
    products = Product.objects.filter(is_active=True)

    context = get_foods_list_context(request, products)
    context['food_groups'] = FoodGroup.objects.all()

    return render(request, 'admin/list_active_foods.html', context)


def list_deactive_foods(request):
    products = Product.objects.filter(is_active=False)

    context = get_foods_list_context(request, products)
    context['food_groups'] = FoodGroup.objects.all()

    return render(request, 'admin/list_deactive_foods.html', context)