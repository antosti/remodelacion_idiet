
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('appointments/', views.appointments_view, name='appointments'),
    path('appointments/new/', views.create_appointment_view, name='create_appointment'),
    path('deactivated-appointments/', views.deactivated_appointments_view, name='deactivated_appointments'),
]


