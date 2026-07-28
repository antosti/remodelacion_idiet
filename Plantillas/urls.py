from django.urls import path
from . import views

urlpatterns = [
    path('list-rules/', views.list_rules, name='list_rules'),
    path('rules/<int:id>/edit/', views.edit_rule, name='edit_rule'),
    path('rules/<int:id>/deactivate/', views.deactivate_rule, name='deactivate_rule'),
    path('rules/deactivate-bulk/', views.deactivate_rules_bulk, name='deactivate_rules_bulk'),
    path('rules/deactivated/', views.list_deactivated_rules, name='list_deactivated_rules'),
    path('rules/<int:id>/reactivate/', views.reactivate_rule, name='reactivate_rule'),
    path('rules/<int:id>/delete/', views.delete_rule, name='delete_rule'),
    path('rules/reactivate-bulk/', views.reactivate_rules_bulk, name='reactivate_rules_bulk'),
    path('rules/delete-bulk/', views.delete_rules_bulk, name='delete_rules_bulk'),
    path('list-templates/', views.list_templates, name='list_templates'),
]
