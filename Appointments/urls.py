
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('appointments/', views.appointments_view, name='appointments'),
    path('appointments/new/', views.create_appointment_view, name='create_appointment'),
    path('appointments/<int:id>/update/', views.update_appointment, name='update_appointment'),
    path('appointments/<int:id>/deactivate/', views.deactivate_appointment, name='deactivate_appointment'),
    path('appointments/<int:id>/reactivate/', views.reactivate_appointment, name='reactivate_appointment'),
    path('appointments/<int:id>/delete/', views.delete_appointment, name='delete_appointment'),
    path('appointments/deactivate-bulk/', views.deactivate_appointments_bulk, name='deactivate_appointments_bulk'),
    path('appointments/reactivate-bulk/', views.reactivate_appointments_bulk, name='reactivate_appointments_bulk'),
    path('appointments/delete-bulk/', views.delete_appointments_bulk, name='delete_appointments_bulk'),
    path('deactivated-appointments/', views.deactivated_appointments_view, name='deactivated_appointments'),
]


