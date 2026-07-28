from django.urls import path
from . import views

urlpatterns = [
    path('list-rules/', views.list_rules, name='list_rules'),
    path('list-templates/', views.list_templates, name='list_templates'),
]
