from django.urls import path
from . import views

urlpatterns = [
    path('create-client/', views.create_client, name='create_client'),
    path('list-active-clients/', views.list_active_clients, name='list_active_clients'),
    path('list-deactive-clients/', views.list_deactive_clients, name='list_deactive_clients'),
    path('clients/<int:id>/deactivate/', views.deactivate_client, name='deactivate_client'),
    path('clients/<int:id>/reactivate/', views.reactivate_client, name='reactivate_client'),
    path('clients/deactivate-bulk/', views.deactivate_clients_bulk, name='deactivate_clients_bulk'),
    path('clients/reactivate-bulk/', views.reactivate_clients_bulk, name='reactivate_clients_bulk'),
]