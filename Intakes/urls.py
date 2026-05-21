from django.urls import path
from . import views

urlpatterns = [
    path('edit-intakes/', views.edit_intakes, name='edit_intakes'),
]