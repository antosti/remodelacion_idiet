import json
from django.contrib import messages

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
            'client_id': appointment.client.id,
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
        messages.error(request, "Faltan datos para crear la cita.")
        return redirect('appointments')

    try:
        client = Client.objects.get(pk=client_id, user_id=request.user.id)
    except Client.DoesNotExist:
        messages.error(request, "El cliente no existe.")
        return redirect('appointments')

    try:
        start_date = datetime.fromisoformat(start_date_value)
        duration = int(duration_minutes)
        if duration <= 0:
            messages.error(request, "La duración de la cita debe ser un número positivo.")
            return redirect('appointments')
    except (ValueError, TypeError):
        messages.error(request, "Formato de fecha o duración inválido.")
        return redirect('appointments')

    if settings.USE_TZ and timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)

    end_date = start_date + timedelta(minutes=duration)

    appointment = Appointment.objects.create(
        user=request.user,
        client=client,
        motive=motive or 'Consulta inicial',
        status='Pendiente',
        start_date=start_date,
        end_date=end_date,
    )

    if appointment:
        messages.success(request, 'Cita creada con exito.')
    else:
        messages.error(request, 'Error al crear la cita. Intentelo de nuevo.')    
    
    return redirect('appointments')


def update_appointment(request, id):
    appointment = Appointment.objects.get(pk=id)

    if appointment:
        client_id = request.POST.get('client_id')
        start_date_value = request.POST.get('start_date')
        duration_minutes = request.POST.get('duration_minutes')
        motive = request.POST.get('motive', 'Consulta inicial').strip()

        if not client_id or not start_date_value or not duration_minutes:
            messages.error(request, "No se puede actualizar la cita sin los datos completos.")
            return redirect('appointments')

        try:
            client = Client.objects.get(pk=client_id, user_id=request.user.id)
        except Client.DoesNotExist:
            messages.error(request, "El cliente no existe.")
            return redirect('appointments')
        
        try:
            start_date = datetime.fromisoformat(start_date_value)
            duration = int(duration_minutes)
            if duration <= 0:
                messages.error(request, "La duración de la cita debe ser un número positivo.")
                return redirect('appointments')
        except (ValueError, TypeError):
            messages.error(request, "Formato de fecha o duración inválido.")
            return redirect('appointments')

        if settings.USE_TZ and timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)

        end_date = start_date + timedelta(minutes=duration)

        appointment.client = client
        appointment.motive = motive
        appointment.start_date = start_date
        appointment.end_date = end_date
        appointment.save()

        messages.success(request, "Cita actualizada correctamente")
    else:
        messages.error(request, "Error al actualizar la cita")
    
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


def deactivate_appointment(request, id):
    try:
        appointment = Appointment.objects.get(pk=id, user_id=request.user.id)
        appointment.status = 'Cancelada'
        appointment.save()
        messages.success(request, 'Cita desactivada correctamente.')
    except Appointment.DoesNotExist:
        messages.error(request, 'La cita no existe.')
    
    return redirect('appointments')


def reactivate_appointment(request, id):
    if request.method != 'POST':
        return redirect('deactivated_appointments')

    try:
        appointment = Appointment.objects.get(pk=id, user_id=request.user.id, status='Cancelada')
        appointment.status = 'Pendiente'
        appointment.save()
        messages.success(request, 'Cita reactivada correctamente.')
    except Appointment.DoesNotExist:
        messages.error(request, 'La cita no existe o no se puede reactivar.')

    return redirect('deactivated_appointments')


def delete_appointment(request, id):
    if request.method != 'POST':
        return redirect('deactivated_appointments')

    try:
        appointment = Appointment.objects.get(pk=id, user_id=request.user.id, status='Cancelada')
        appointment.delete()
        messages.success(request, 'Cita eliminada definitivamente.')
    except Appointment.DoesNotExist:
        messages.error(request, 'La cita no existe o no se puede eliminar.')

    return redirect('deactivated_appointments')


def reactivate_appointments_bulk(request):
    if request.method != 'POST':
        return redirect('deactivated_appointments')

    appointment_ids = request.POST.getlist('appointment_ids')

    if not appointment_ids:
        messages.error(request, 'Selecciona al menos una cita para reactivar.')
        return redirect('deactivated_appointments')

    try:
        appointments = Appointment.objects.filter(
            pk__in=appointment_ids,
            user_id=request.user.id,
            status='Cancelada'
        )

        if appointments.exists():
            count = appointments.count()
            appointments.update(status='Pendiente')
            messages.success(request, f'{count} cita(s) reactivada(s) correctamente.')
        else:
            messages.error(request, 'No se encontraron citas para reactivar.')
    except Exception:
        messages.error(request, 'Error al reactivar las citas.')

    return redirect('deactivated_appointments')


def delete_appointments_bulk(request):
    if request.method != 'POST':
        return redirect('deactivated_appointments')

    appointment_ids = request.POST.getlist('appointment_ids')

    if not appointment_ids:
        messages.error(request, 'Selecciona al menos una cita para eliminar.')
        return redirect('deactivated_appointments')

    try:
        appointments = Appointment.objects.filter(
            pk__in=appointment_ids,
            user_id=request.user.id,
            status='Cancelada'
        )

        if appointments.exists():
            count = appointments.count()
            appointments.delete()
            messages.success(request, f'{count} cita(s) eliminada(s) definitivamente.')
        else:
            messages.error(request, 'No se encontraron citas para eliminar.')
    except Exception:
        messages.error(request, 'Error al eliminar las citas.')

    return redirect('deactivated_appointments')


def deactivate_appointments_bulk(request):
    if request.method != 'POST':
        return redirect('appointments')
    
    appointment_ids = request.POST.getlist('appointment_ids')
    
    if not appointment_ids:
        messages.error(request, 'Selecciona al menos una cita para desactivar.')
        return redirect('appointments')
    
    try:
        appointments = Appointment.objects.filter(
            pk__in=appointment_ids,
            user_id=request.user.id
        )
        
        if appointments.exists():
            count = appointments.count()
            appointments.update(status='Cancelada')
            messages.success(request, f'{count} cita(s) desactivada(s) correctamente.')
        else:
            messages.error(request, 'No se encontraron citas para desactivar.')
    except Exception as e:
        messages.error(request, 'Error al desactivar las citas.')
    
    return redirect('appointments')
