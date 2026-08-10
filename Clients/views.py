from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django.shortcuts import render, redirect, get_object_or_404
from Users.models import User
from Clients.models import Client, ClientMeasurementHistory
from FoodGroup.models import FoodGroup, FoodGroupExcluded
from Products.models import ProductExcluded
from idiet.views import paginate_queryset
from django.contrib.auth.decorators import login_required


def normalize_decimal(value):
    if value is None:
        return value
    return value.replace(',', '.')


def record_measurement_history(client):
    current_values = {
        'height': client.height,
        'weight': client.weight,
        'metabolismo_basal': client.metabolismo_basal,
        'gasto_energetico': client.gasto_energetico,
        'imc': client.imc,
    }

    last_entry = ClientMeasurementHistory.objects.filter(client=client).order_by('-updated_at').first()
    if last_entry and all(getattr(last_entry, field) == value for field, value in current_values.items()):
        return

    ClientMeasurementHistory.objects.create(client=client, **current_values)


def sync_excluded_products(client, product_ids):
    try:
        desired_ids = {int(product_id) for product_id in product_ids if product_id}
    except ValueError:
        desired_ids = set()

    existing_ids = set(
        ProductExcluded.objects.filter(client=client).values_list('product_id', flat=True)
    )

    ids_to_remove = existing_ids - desired_ids
    ids_to_add = desired_ids - existing_ids

    if ids_to_remove:
        ProductExcluded.objects.filter(client=client, product_id__in=ids_to_remove).delete()

    for product_id in ids_to_add:
        ProductExcluded.objects.create(client=client, product_id=product_id)


def sync_excluded_food_groups(client, food_group_ids):
    try:
        desired_ids = {int(food_group_id) for food_group_id in food_group_ids if food_group_id}
    except ValueError:
        desired_ids = set()

    existing_ids = set(
        FoodGroupExcluded.objects.filter(client=client).values_list('food_group_id', flat=True)
    )

    ids_to_remove = existing_ids - desired_ids
    ids_to_add = desired_ids - existing_ids

    if ids_to_remove:
        FoodGroupExcluded.objects.filter(client=client, food_group_id__in=ids_to_remove).delete()

    for food_group_id in ids_to_add:
        FoodGroupExcluded.objects.create(client=client, food_group_id=food_group_id)

@login_required
def create_client(request):
    food_groups = FoodGroup.objects.all()

    if request.method == 'POST':
        user = User.objects.get(id=request.user.id)
        try:
            # Then create the client profile using the submitted form data
            client = Client.objects.create(
                user=user,
                email=request.POST.get('email'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                birth_date=request.POST.get('birth_date'),
                gender=request.POST.get('gender'),
                height=request.POST.get('height') or None,
                weight=normalize_decimal(request.POST.get('weight')) or None,
                dni=request.POST.get('dni'),
                phone_number=request.POST.get('phone_number') or '',
                phone_number_2=request.POST.get('phone_number_2') or '',
                address=request.POST.get('address') or '',
                postal_code=request.POST.get('postal_code') or '',
                city=request.POST.get('city') or '',
                activity_level=request.POST.get('activity_level'),
                metabolismo_basal=normalize_decimal(request.POST.get('metabolismo_basal')) or None,
                gasto_energetico=normalize_decimal(request.POST.get('gasto_energetico')) or None,
                imc=normalize_decimal(request.POST.get('imc')) or None,
            )
        except (ValidationError, ValueError, IntegrityError):
            messages.error(request, 'Revisa el peso y la altura: deben ser valores numéricos.')
            return redirect('create_client')

        sync_excluded_products(client, request.POST.getlist('excluded_products'))
        sync_excluded_food_groups(client, request.POST.getlist('excluded_food_groups'))
        record_measurement_history(client)
        messages.success(request, "Cliente creado correctamente")

        return redirect('create_client')

    return render(request, 'admin/create_client.html', {
        'food_groups': food_groups,
        'excluded_products_data': [],
        'excluded_food_groups_data': [],
    })

@login_required
def client_detail(request, id):
    client = get_object_or_404(Client, id=id)

    if request.method == 'POST':
        client.dni = request.POST.get('dni')
        client.first_name = request.POST.get('first_name')
        client.last_name = request.POST.get('last_name')
        client.email = request.POST.get('email')
        client.birth_date = request.POST.get('birth_date')
        client.gender = request.POST.get('gender')
        client.height = request.POST.get('height') or None
        client.weight = normalize_decimal(request.POST.get('weight')) or None
        client.activity_level = request.POST.get('activity_level')
        client.phone_number = request.POST.get('phone_number') or ''
        client.phone_number_2 = request.POST.get('phone_number_2') or ''
        client.address = request.POST.get('address') or ''
        client.postal_code = request.POST.get('postal_code') or ''
        client.city = request.POST.get('city') or ''
        client.metabolismo_basal = normalize_decimal(request.POST.get('metabolismo_basal')) or None
        client.gasto_energetico = normalize_decimal(request.POST.get('gasto_energetico')) or None
        client.imc = normalize_decimal(request.POST.get('imc')) or None

        try:
            client.save()
        except (ValidationError, ValueError, IntegrityError):
            messages.error(request, 'Revisa el peso y la altura: deben ser valores numéricos.')
            return redirect('client_detail', id=client.id)

        sync_excluded_products(client, request.POST.getlist('excluded_products'))
        sync_excluded_food_groups(client, request.POST.getlist('excluded_food_groups'))
        record_measurement_history(client)

        messages.success(request, 'Cliente actualizado correctamente')
        return redirect('client_detail', id=client.id)

    food_groups = FoodGroup.objects.all()
    excluded_products_data = [
        {'id': exclusion.product_id, 'name': exclusion.product.food_name_spanish}
        for exclusion in ProductExcluded.objects.filter(client=client).select_related('product')
    ]
    excluded_food_groups_data = [
        {'id': exclusion.food_group_id, 'name': exclusion.food_group.name}
        for exclusion in FoodGroupExcluded.objects.filter(client=client).select_related('food_group')
    ]

    return render(request, 'admin/client_detail.html', {
        'client': client,
        'food_groups': food_groups,
        'excluded_products_data': excluded_products_data,
        'excluded_food_groups_data': excluded_food_groups_data,
    })

@login_required
def get_clients_list_context(request, clients):
    first_name = request.GET.get('first_name', '').strip()
    last_name = request.GET.get('last_name', '').strip()
    dni = request.GET.get('dni', '').strip()

    if first_name:
        clients = clients.filter(first_name__icontains=first_name)

    if last_name:
        clients = clients.filter(last_name__icontains=last_name)

    if dni:
        clients = clients.filter(dni__icontains=dni)

    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    allowed_sorts = {
        'dni': 'dni',
        'name': 'first_name',
        'last_name': 'last_name',
        'contact': 'email',
    }

    current_sort = sort if sort in allowed_sorts else 'name'
    current_direction = 'desc' if direction == 'desc' else 'asc'

    order_field = allowed_sorts[current_sort]

    if current_direction == 'desc':
        order_field = f'-{order_field}'

    clients = clients.order_by(order_field)

    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    pagination = paginate_queryset(request, clients)

    return {
        'clients': pagination['page_obj'],
        'current_sort': current_sort,
        'current_direction': current_direction,
        'first_name': first_name,
        'last_name': last_name,
        'dni': dni,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
    }

@login_required
def deactivate_client(request, id):
    if request.method == 'POST':
        client = get_object_or_404(Client, id=id, status=True)
        client.status = False
        client.save()
        messages.success(request, 'Cliente desactivado correctamente')
    return redirect('list_active_clients')

@login_required
def reactivate_client(request, id):
    if request.method == 'POST':
        client = get_object_or_404(Client, id=id, status=False)
        client.status = True
        client.save()
        messages.success(request, 'Cliente reactivado correctamente')
    return redirect('list_deactive_clients')

@login_required
def deactivate_clients_bulk(request):
    if request.method == 'POST':
        client_ids = request.POST.getlist('selected_clients')
        clients = Client.objects.filter(id__in=client_ids, status=True)
        count = 0
        for client in clients:
            client.status = False
            client.save()
            count += 1

        if count:
            messages.success(request, f'{count} cliente(s) desactivado(s) correctamente')
        else:
            messages.warning(request, 'No se seleccionaron clientes válidos para desactivar')
    return redirect('list_active_clients')

@login_required
def reactivate_clients_bulk(request):
    if request.method == 'POST':
        client_ids = request.POST.getlist('selected_clients')
        clients = Client.objects.filter(id__in=client_ids, status=False)
        count = 0
        for client in clients:
            client.status = True
            client.save()
            count += 1

        if count:
            messages.success(request, f'{count} cliente(s) reactivado(s) correctamente')
        else:
            messages.warning(request, 'No se seleccionaron clientes válidos para reactivar')
    return redirect('list_deactive_clients')

@login_required
def list_active_clients(request):
    clients = Client.objects.filter(status=True)
    context = get_clients_list_context(request, clients)
    return render(request, 'admin/list_active_clients.html', context)


@login_required
def list_deactive_clients(request):
    clients = Client.objects.filter(status=False)
    context = get_clients_list_context(request, clients)
    return render(request, 'admin/list_deactive_clients.html', context)