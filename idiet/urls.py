"""
URL configuration for idiet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_page),
    path('admin-home/', views.admin_home),
    path('create-client/', views.create_client, name='create_client'),
    path('list-active-foods/', views.list_active_foods, name='list_active_foods'),
    path('create-food/', views.create_food, name='create_food'),
    # path('about/',),
    # path('users/', include('Users.urls')),
    # path('clients/', include('Clients.urls')),
    # path('products/', include('Products.urls')),
    # path('dishes/', include('Dishes.urls')),
    # path('menus/', include('Menus.urls')),
    # path('intakes/', include('Intakes.urls')),
    # path('appointments/', include('Appointments.urls')),
    # path('allergens/', include('Allergens.urls')),
    # path('micronutrients/', include('Micronutrients.urls')),
    # path('plantillas/', include('Plantillas.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
