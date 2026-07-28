from django.urls import path
from . import views

urlpatterns = [
    path('list-rules/', views.list_rules, name='list_rules'),
    path('rules/<int:id>/edit/', views.edit_rule, name='edit_rule'),
    path('rules/<int:id>/deactivate/', views.deactivate_rule, name='deactivate_rule'),
    path('rules/deactivate-bulk/', views.deactivate_rules_bulk, name='deactivate_rules_bulk'),
    path('list-templates/', views.list_templates, name='list_templates'),
]
