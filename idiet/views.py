from django.http import HttpResponse
from django.shortcuts import render, redirect
from Users.models import User
from Clients.models import Client
from Dishes.models import Dish
from decimal import Decimal, InvalidOperation
from Micronutrients.models import Micronutrient
from Products.models import Product, ProductMicronutrient
from Menus.models import Menu
from Appointments.models import Appointment
from FoodGroup.models import FoodGroup
from SuperGroup.models import SuperGroup
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def home_page(request):
    # return HttpResponse("Hello world! This is the home page.")
    return render(request, 'home.html')

@login_required
def admin_home(request):
    # Dashboard counters
    client = Client.objects.all().count()
    dish = Dish.objects.all().count()
    product = Product.objects.all().count()
    menu = Menu.objects.all().count()
    appointment = Appointment.objects.all().count()

    recent_appointment = Appointment.objects.order_by('-id').first()

    # Get today's first 3 appointments with related client data
    today = timezone.localdate()
    agenda_client = Appointment.objects.select_related('client').filter(
        start_date__date=today
    ).order_by('start_date')[:3]

    new_client = Client.objects.select_related('user').order_by('-user__date_joined').first()

    user = request.user

    return render(request, 'admin/home.html', {
        'client': client,
        'dish': dish,
        'product': product,
        'menu': menu,
        'appointment': appointment,
        'recent_appointment': recent_appointment,
        'agenda_client': agenda_client,
        'current_user': user,
        'new_client': new_client,
    })


def create_client(request):
    food_groups = FoodGroup.objects.all()

    if request.method == 'POST':
        # First create the Django user linked to the client
        user = User.objects.create_user(
            email=request.POST.get('email'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            username=request.POST.get('username'),
        )

        # Then create the client profile using the submitted form data
        Client.objects.create(
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

        return redirect('create_client')

    return render(request, 'admin/create_client.html', {
        'food_groups': food_groups,
    })


def list_active_foods(request):
    food_groups = FoodGroup.objects.all()
    products = Product.objects.all()

    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    # Only allow sorting by safe predefined fields
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

    # Django uses "-" before a field name for descending order
    if current_direction == 'desc':
        order_field = f'-{order_field}'

    products = products.order_by(order_field)

    # Keep current query parameters when changing pages
    page_params = request.GET.copy()
    page_params.pop('page', None)

    # Keep filters, but remove current sorting values when changing sort column
    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    page_url_prefix = f'?{page_params.urlencode()}&' if page_params else '?'
    sort_url_prefix = f'?{sort_params.urlencode()}&' if sort_params else '?'

    paginator = Paginator(products, 100)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'admin/list_active_foods.html', {
        'food_groups': food_groups,
        'products': products,
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': page_url_prefix,
        'sort_url_prefix': sort_url_prefix,
    })


def create_food(request):
    food_groups = FoodGroup.objects.all()
    super_groups = SuperGroup.objects.all()

    # Maps form input names to Micronutrient names stored in the database
    micronutrient_fields = {
        'water': 'Agua',
        'fiber': 'Fibra',
        'pc': 'PC',
        'ags_total': 'AGS totales',
        'agm_total': 'AGM totales',
        'agp_total': 'AGP totales',
        'cholesterol': 'Colesterol',

        'vit_a': 'Vit A',
        'carotenes': 'Carotenos',
        'vit_b1': 'Tiamina B1',
        'vit_b2': 'Riboflavina B2',
        'vit_b3': 'Niacina B3',
        'vit_b5': 'Ac. Pantoténico B5',
        'vit_b6': 'Piridoxina B6',
        'biotin': 'Biotina',
        'vit_b9': 'Ac. Fólico B9',
        'vit_b12': 'Cobalamina B12',
        'vit_c': 'Vit C',
        'vit_d': 'Vit D',
        'tocopherol': 'Tocoferol',
        'vit_e': 'Vit E',
        'vit_k': 'Vit K',
        'purines': 'Purinas',

        'sodium': 'Sodio',
        'potassium': 'Potasio',
        'magnesium': 'Magnesio',
        'calcium': 'Calcio',
        'phosphorus': 'Fósforo',
        'iron': 'Hierro',
        'chlorine': 'Cloro',
        'zinc': 'Zinc',
        'copper': 'Cobre',
        'manganese': 'Manganeso',
        'chromium': 'Cromo',
        'cobalt': 'Cobalto',
        'molybdenum': 'Molibdo',
        'iodine': 'Yodo',
        'fluorine': 'Flúor',

        'butyric': 'Butírico C4:0',
        'caproic': 'Caproico C6:0',
        'caprylic': 'Caprílico C8:0',
        'capric': 'Cáprico C10:0',
        'lauric': 'Lárico C12:0',
        'myristic': 'Mirístico C14:0',
        'c15': 'C15:0',
        'c1500': 'C15:00',
        'c16': 'Palmítico C16:0',
        'c17': 'C17:0',
        'c1700': 'C17:00',
        'c18': 'Esteárico C18:0',
        'c20': 'Araquídico C20:0',
        'c22': 'Behénico C22:0',
        'c141': 'Miristol C14:1',
        'c161': 'Palmitole C16:1',
        'c181': 'Oleico C18:1',
        'c201': 'Eicoseno C20:1',
        'c221': 'C22:1',
        'c182': 'Linoleico C18:2',
        'c183': 'Linolénico C18:3',
        'c184': 'C18:4',
        'c204': 'Araquidónico C20:4',
        'c205': 'C20:5',
        'c225': 'C22:5',
        'c226': 'C22:6',
        'satura': 'Otros satura',
        'insatura': 'Otros insatura',
        'omega3': 'Omega 3:0',
        'etanol': 'Etanol',
    }

    def get_decimal_value(field_name):
        # Convert empty or invalid numeric inputs to Decimal zero
        raw_value = request.POST.get(field_name, '').strip()
        if raw_value == '':
            return Decimal('0.00')

        try:
            return Decimal(raw_value)
        except InvalidOperation:
            return Decimal('0.00')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        english_name = request.POST.get('english_name', '').strip()
        super_group_ids = request.POST.getlist('super_group')

        # Load micronutrients once and access them by name during product creation
        micronutrients = {
            micronutrient.name: micronutrient
            for micronutrient in Micronutrient.objects.all()
        }

        # Ensure the product and its micronutrients are created as one atomic operation
        with transaction.atomic():
            product = Product.objects.create(
                food_name=name,
                food_name_spanish=name,
                food_name_eng=english_name or name,
                origin_db='Act. i-Diet',
                ed_porc=100,
                kcal_100g=get_decimal_value('kcal_100g'),
                prot_g=get_decimal_value('proteins'),
                ch_g=get_decimal_value('hydrates'),
                fat_g=get_decimal_value('fats'),
                food_group_id=request.POST.get('food_group') or None,
            )

            if super_group_ids:
                product.super_groups.set(super_group_ids)

            # Create only micronutrient values that are present and greater than zero
            for input_name, micronutrient_name in micronutrient_fields.items():
                micronutrient = micronutrients.get(micronutrient_name)
                if not micronutrient:
                    continue

                value = get_decimal_value(input_name)

                if value != Decimal('0.00'):
                    ProductMicronutrient.objects.create(
                        product=product,
                        micronutrient=micronutrient,
                        value=value,
                    )

        return redirect('create_food')

    return render(request, 'admin/create_food.html', {
        'food_groups': food_groups,
        'super_groups': super_groups,
    })


def list_clients(request):
    clients = Client.objects.all()

    first_name = request.GET.get('first_name', '').strip()
    last_name = request.GET.get('last_name', '').strip()
    dni = request.GET.get('dni', '').strip()

    # Apply filters only when the corresponding field has a value
    if first_name:
        clients = clients.filter(first_name__icontains=first_name)

    if last_name:
        clients = clients.filter(last_name__icontains=last_name)

    if dni:
        clients = clients.filter(dni__icontains=dni)

    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    # Public sort keys are mapped to real model fields
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

    # Preserve active filters and sorting while navigating between pages
    page_params = request.GET.copy()
    page_params.pop('page', None)

    # Preserve filters while replacing the current sorting parameters
    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    page_url_prefix = f'?{page_params.urlencode()}&' if page_params else '?'
    sort_url_prefix = f'?{sort_params.urlencode()}&' if sort_params else '?'

    paginator = Paginator(clients, 100)
    page_number = request.GET.get('page')
    clients = paginator.get_page(page_number)

    return render(request, 'admin/list_clients.html', {
        'clients': clients,
        'current_sort': current_sort,
        'current_direction': current_direction,
        'first_name': first_name,
        'last_name': last_name,
        'dni': dni,
        'page_url_prefix': page_url_prefix,
        'sort_url_prefix': sort_url_prefix,
    })

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("admin-home")
        else:
            messages.error(request, "Email o contraseña incorrectos")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("home")

