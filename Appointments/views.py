import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta

from Appointments.models import Appointment
from Clients.models import Client
from idiet.views import paginate_queryset

# Create your views here.

def appointments_view(request):
    per_page = int(request.GET.get("per_page", 10))
    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    allowed_sorts = {
        'name': 'client__first_name',
        'surname': 'client__last_name',
        'email': 'client__email',
        'date': 'start_date',
    }

    current_sort = sort if sort in allowed_sorts else 'name'
    current_direction = 'desc' if direction == 'desc' else 'asc'

    order_field = allowed_sorts[current_sort]

    if current_direction == 'desc':
        order_field = f'-{order_field}'


    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    appointments = Appointment.objects.filter(status='Pendiente', user_id=request.user.id)
    appointments = appointments.order_by(order_field)
    pagination = paginate_queryset(request, appointments, per_page)
    clients = Client.objects.filter(user_id=request.user.id)

    appointment_events = [
        {
            'id': appointment.id,
            'title': f'{appointment.client.first_name} {appointment.client.last_name}',
            'start': timezone.localtime(appointment.start_date).strftime('%Y-%m-%dT%H:%M:%S'),
            'end': timezone.localtime(appointment.end_date).strftime('%Y-%m-%dT%H:%M:%S'),
            'description': appointment.motive,
        }
        for appointment in appointments
    ]

    return render(request, 'admin/appointments.html', {
        'appointments': pagination['page_obj'],
        'clients': clients,
        'appointment_events': json.dumps(appointment_events, cls=DjangoJSONEncoder),
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
        "per_page": per_page,
    })


def create_appointment_view(request):
    if request.method != 'POST':
        return redirect('appointments')

    client_id = request.POST.get('client_id')
    start_date_value = request.POST.get('start_date')
    duration_minutes = request.POST.get('duration_minutes')
    motive = request.POST.get('motive', 'Consulta inicial').strip()

    if not client_id or not start_date_value or not duration_minutes:
        return redirect('appointments')

    try:
        client = Client.objects.get(pk=client_id, user_id=request.user.id)
    except Client.DoesNotExist:
        return redirect('appointments')

    try:
        start_date = datetime.fromisoformat(start_date_value)
        duration = int(duration_minutes)
        if duration <= 0:
            return redirect('appointments')
    except (ValueError, TypeError):
        return redirect('appointments')

    if settings.USE_TZ and timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)

    end_date = start_date + timedelta(minutes=duration)

    Appointment.objects.create(
        user=request.user,
        client=client,
        motive=motive or 'Consulta inicial',
        status='Pendiente',
        start_date=start_date,
        end_date=end_date,
    )

    return redirect('appointments')

def deactivated_appointments_view(request):
    per_page = int(request.GET.get("per_page", 10))
    sort = request.GET.get('sort', 'name').strip()
    direction = request.GET.get('direction', 'asc').strip()

    allowed_sorts = {
        'name': 'client__first_name',
        'surname': 'client__last_name',
        'email': 'client__email',
        'date': 'start_date',
    }

    current_sort = sort if sort in allowed_sorts else 'name'
    current_direction = 'desc' if direction == 'desc' else 'asc'

    order_field = allowed_sorts[current_sort]

    if current_direction == 'desc':
        order_field = f'-{order_field}'


    sort_params = request.GET.copy()
    sort_params.pop('page', None)
    sort_params.pop('sort', None)
    sort_params.pop('direction', None)

    appointments = Appointment.objects.filter(status='Cancelada', user_id=request.user.id)
    appointments = appointments.order_by(order_field)
    pagination = paginate_queryset(request, appointments, per_page)

    return render(request, 'admin/deactivatedAppointments.html', {
        'appointments': pagination['page_obj'],
        'current_sort': current_sort,
        'current_direction': current_direction,
        'page_url_prefix': pagination['page_url_prefix'],
        'sort_url_prefix': f'?{sort_params.urlencode()}&' if sort_params else '?',
        "per_page": per_page,
    })
