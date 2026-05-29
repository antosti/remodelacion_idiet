from django.contrib import messages

from django.shortcuts import render, redirect
from Users.models import User
from Clients.models import Client
from FoodGroup.models import FoodGroup
from idiet.views import paginate_queryset
from django.contrib.auth.decorators import login_required

@login_required
def create_client(request):
    food_groups = FoodGroup.objects.all()

    if request.method == 'POST':
        # First create the Django user linked to the client
        user = User.objects.create_user(
            email=request.POST.get('email'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            username=request.POST.get('first_name'),
        )

        # Then create the client profile using the submitted form data
        client = Client.objects.create(
            user=user,
            email=request.POST.get('email'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            birth_date=request.POST.get('birth_date'),
            gender=request.POST.get('gender'),
            height=request.POST.get('height'),
            weight=request.POST.get('weight'),
            dni=request.POST.get('dni'),
            phone_number=request.POST.get('phone_number') or '',
            phone_number_2=request.POST.get('phone_number_2') or '',
            address=request.POST.get('address') or '',
            postal_code=request.POST.get('postal_code') or '',
            city=request.POST.get('city') or '',
            activity_level=request.POST.get('activity_level'),
        )

        if(user is not None and client is not None):
            messages.success(request, "Cliente creado correctamente")
        else:
            messages.error(request, "Error al crear el cliente")

        return redirect('create_client')

    return render(request, 'admin/create_client.html', {
        'food_groups': food_groups,
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
def list_active_clients(request):
    clients = Client.objects.select_related('user').filter(user__is_active=True)
    context = get_clients_list_context(request, clients)
    return render(request, 'admin/list_active_clients.html', context)


@login_required
def list_deactive_clients(request):
    clients = Client.objects.select_related('user').filter(user__is_active=False)
    context = get_clients_list_context(request, clients)
    return render(request, 'admin/list_deactive_clients.html', context)