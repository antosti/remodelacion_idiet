from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.contrib import messages

from Dishes.models import Dish
from Intakes.models import Intake
from Products.models import Product
from idiet.views import paginate_queryset
from django.contrib.auth.decorators import login_required

INTAKE_COLORS = [
    '#f2b705', '#f4d29e', '#a7ad1e', '#6b7a1f', '#8c1c3f',
    '#f0a878', '#c9c8f5', '#8f8ef0', '#4b1a6b', '#e8623f',
]


@login_required
def edit_intakes(request):
    if request.method == 'POST':
        dish_ids = request.POST.getlist('dish_ids')
        save_failed = False

        for dish_id in dish_ids:
            try:
                dish = Dish.objects.get(pk=dish_id)
                intake_ids = request.POST.getlist(f'intakes_dish_{dish_id}')
                dish.intakes.set(intake_ids)
            except Dish.DoesNotExist:
                save_failed = True

        if dish_ids:
            if save_failed:
                messages.error(request, 'Error al actualizar las ingestas. Intentelo de nuevo.')
            else:
                messages.success(request, 'Ingestas actualizadas con éxito.')

        query_params = {
            'intake_filter': request.POST.get('intake_filter', ''),
            'dish_name': request.POST.get('dish_name', ''),
            'product_filter': request.POST.get('product_filter', ''),
            'sort': request.POST.get('sort', ''),
            'direction': request.POST.get('direction', ''),
            'page': request.POST.get('page', ''),
        }
        query_params = {key: value for key, value in query_params.items() if value}

        return redirect(f"{request.path}?{urlencode(query_params)}")

    intake_filter = request.GET.get('intake_filter', '').strip()
    dish_name = request.GET.get('dish_name', '').strip()
    product_filter = request.GET.get('product_filter', '').strip()
    current_sort = request.GET.get('sort', 'name')
    current_direction = request.GET.get('direction', 'asc')

    intakes = list(Intake.objects.all().order_by('order'))
    for index, intake in enumerate(intakes):
        intake.color = INTAKE_COLORS[index % len(INTAKE_COLORS)]

    products = Product.objects.all().order_by('food_name_spanish')
    dishes = Dish.objects.prefetch_related('intakes').all()

    if intake_filter:
        dishes = dishes.filter(intakes__id=intake_filter)

    if dish_name:
        dishes = dishes.filter(name__icontains=dish_name)

    if product_filter:
        dishes = dishes.filter(product__id=product_filter)

    if current_sort != 'name':
        current_sort = 'name'

    order_field = current_sort

    if current_direction == 'desc':
        order_field = f'-{order_field}'
    else:
        current_direction = 'asc'

    dishes = dishes.distinct().order_by(order_field)

    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    pagination = paginate_queryset(request, dishes)

    for dish in pagination['page_obj']:
        dish.intake_id_set = {intake.id for intake in dish.intakes.all()}

    return render(request, 'admin/edit_intakes.html', {
        'dish_list': pagination['page_obj'],
        'intakes': intakes,
        'products': products,
        'intake_filter': intake_filter,
        'dish_name': dish_name,
        'product_filter': product_filter,
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
    })