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
    path('templates/create/', views.create_template, name='create_template'),
    path('templates/<int:id>/', views.template_detail, name='template_detail'),
    path('templates/<int:id>/edit/', views.edit_template, name='edit_template'),
    path('templates/<int:template_id>/intake/<int:item_id>/edit/', views.edit_template_intake, name='edit_template_intake'),
    path('templates/<int:template_id>/intake/<int:item_id>/copy/', views.copy_template_intake, name='copy_template_intake'),
    path('templates/<int:id>/deactivate/', views.deactivate_template, name='deactivate_template'),
    path('templates/deactivate-bulk/', views.deactivate_templates_bulk, name='deactivate_templates_bulk'),
    path('templates/deactivated/', views.list_deactivated_templates, name='list_deactivated_templates'),
    path('templates/<int:id>/reactivate/', views.reactivate_template, name='reactivate_template'),
    path('templates/reactivate-bulk/', views.reactivate_templates_bulk, name='reactivate_templates_bulk'),
    path('templates/<int:id>/delete/', views.delete_template, name='delete_template'),
    path('templates/delete-bulk/', views.delete_templates_bulk, name='delete_templates_bulk'),
]
