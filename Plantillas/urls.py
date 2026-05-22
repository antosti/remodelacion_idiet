from django.urls import path
from . import views

urlpatterns = [
    path('list-templates/', views.list_templates, name='list_templates'),
]