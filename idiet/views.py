from django.http import HttpResponse
from django.shortcuts import render, redirect
from Users.models import User
from Clients.models import Client
from Dishes.models import Dish
from Products.models import Product
from Menus.models import Menu
from Appointments.models import Appointment
from FoodGroup.models import FoodGroup
from django.utils import timezone
from django.core.paginator import Paginator

def home_page(request):
    # return HttpResponse("Hello world! This is the home page.")
    return render(request, 'home.html')

def admin_home(request):
    client = Client.objects.all().count()
    dish = Dish.objects.all().count()
    product = Product.objects.all().count()
    menu = Menu.objects.all().count()
    appointment = Appointment.objects.all().count()

    recent_appointment = Appointment.objects.order_by('-id').first()

    today = timezone.localdate()
    agenda_client = Appointment.objects.select_related('client').filter(
        start_date__date=today
    ).order_by('start_date')[:3]

    new_client = Client.objects.select_related('user').order_by('-user__date_joined').first()

    user = request.user

    return render(request, 'admin/home.html', {
        'client' : client,
        'dish' : dish,
        'product' : product,
        'menu' : menu,
        'appointment' : appointment,
        'recent_appointment' : recent_appointment,
        'agenda_client' : agenda_client,
        'current_user' : user,
        'new_client' : new_client,
    })

def create_client(request):
    food_groups = FoodGroup.objects.all()

    if request.method == 'POST':
        user = User.objects.create_user(
            email=request.POST.get('email'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            username=request.POST.get('username'),
        )

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

    paginator = Paginator(products, 100)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'admin/list_active_foods.html',  {
        'food_groups': food_groups,
        'products': products,
        'current_sort': current_sort,
        'current_direction': current_direction,
    })