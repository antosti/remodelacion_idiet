from django.urls import path
from . import views

urlpatterns = [
    path('clients/<int:id>/create-diet/', views.create_diet, name='create_diet'),
]
