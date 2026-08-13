from django.shortcuts import render
from Clients.models import Client
from Dishes.models import Dish
from Products.models import Product
from Menus.models import Menu
from Appointments.models import Appointment
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from idiet.permissions import scoped_queryset


def home_page(request):
    return render(request, 'home.html')

@login_required
def admin_home(request):
    clients_qs = scoped_queryset(Client.objects.all(), request.user)
    appointments_qs = scoped_queryset(Appointment.objects.all(), request.user)

    # Dashboard counters
    client = clients_qs.count()
    dish = scoped_queryset(Dish.objects.filter(active=True), request.user, include_unassigned=True).count()
    product = scoped_queryset(Product.objects.all(), request.user, include_unassigned=True).count()
    menu = Menu.objects.all().count()
    appointment = appointments_qs.exclude(status='Cancelada').count()

    recent_appointment = appointments_qs.order_by('-id').first()

    # Get today's first 3 appointments with related client data
    today = timezone.localdate()
    agenda_client = appointments_qs.select_related('client').filter(
        start_date__date=today
    ).order_by('start_date')[:3]

    new_client = clients_qs.select_related('user').order_by('-user__date_joined').first()

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


def paginate_queryset(request, queryset, per_page=10):
    page_params = request.GET.copy()
    page_params.pop('page', None)

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return {
        'page_obj': page_obj,
        'page_url_prefix': f'?{page_params.urlencode()}&' if page_params else '?',
    }