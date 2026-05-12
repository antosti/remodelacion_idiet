from django.urls import path
from . import views

urlpatterns = [
    path('create-client/', views.create_client, name='create_client'),
    path('list-active-clients/', views.list_active_clients, name='list_active_clients'),
    path('list-deactive-clients/', views.list_deactive_clients, name='list_deactive_clients'),
]