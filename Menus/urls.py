from django.urls import path
from . import views

urlpatterns = [
    path('clients/<int:id>/create-diet/', views.create_diet, name='create_diet'),
    path('clients/<int:id>/diets/', views.client_diets, name='client_diets'),
    path('clients/<int:client_id>/diets/<int:menu_id>/', views.diet_detail, name='diet_detail'),
    path('clients/<int:client_id>/diets/<int:menu_id>/intake/<int:item_id>/edit/',
         views.edit_menu_intake, name='edit_menu_intake'),
    path('clients/<int:client_id>/diets/<int:menu_id>/intake/<int:item_id>/copy/',
         views.copy_menu_intake, name='copy_menu_intake'),
    path('clients/<int:client_id>/diets/<int:menu_id>/add-intake/',
         views.add_menu_intake, name='add_menu_intake'),
    path('clients/<int:client_id>/diets/<int:menu_id>/remove-intake/',
         views.remove_menu_intake, name='remove_menu_intake'),
    path('clients/<int:client_id>/diets/<int:menu_id>/regenerate/',
         views.regenerate_menu, name='regenerate_menu'),
    path('clients/<int:client_id>/diets/<int:menu_id>/delete/',
         views.delete_menu, name='delete_menu'),
    path('clients/<int:client_id>/diets/<int:menu_id>/save-as-template/',
         views.save_menu_as_template, name='save_menu_as_template'),
    path('clients/<int:client_id>/diets/<int:menu_id>/pdf/',
         views.download_menu_pdf, name='download_menu_pdf'),
    path('clients/<int:client_id>/diets/<int:menu_id>/send-pdf/',
         views.send_menu_pdf, name='send_menu_pdf'),
]
