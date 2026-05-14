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
from django.contrib import messages


def home_page(request):
    # return HttpResponse("Hello world! This is the home page.")
    return render(request, 'home.html')


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

def paginate_queryset(request, queryset, per_page=100):
    page_params = request.GET.copy()
    page_params.pop('page', None)

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return {
        'page_obj': page_obj,
        'page_url_prefix': f'?{page_params.urlencode()}&' if page_params else '?',
    }