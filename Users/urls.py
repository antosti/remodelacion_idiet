
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('recuperar-contrasena/', views.password_reset_request, name='password_reset_request'),
    path('restablecer-contrasena/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
]


