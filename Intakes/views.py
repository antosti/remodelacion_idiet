from django.shortcuts import render

from Dishes.models import Dish
from Intakes.models import Intake
from Products.models import Product
from idiet.views import paginate_queryset
from django.contrib.auth.decorators import login_required

@login_required
def edit_intakes(request):
    intake_filter = request.GET.get('intake_filter', '').strip()
    dish_name = request.GET.get('dish_name', '').strip()
    product_filter = request.GET.get('product_filter', '').strip()
    current_sort = request.GET.get('sort', 'name')
    current_direction = request.GET.get('direction', 'asc')

    intakes = Intake.objects.all().order_by('order')
    products = Product.objects.all().order_by('food_name_spanish')
    dishes = Dish.objects.all()

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