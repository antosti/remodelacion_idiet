from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    dni = models.CharField(max_length=200, blank=True, null=True)
    poblacion = models.CharField(max_length=200, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    provincia = models.CharField(max_length=200, blank=True, null=True)
    forma_pago = models.CharField(max_length=200, blank=True, null=True)
    iban = models.CharField(max_length=200, blank=True, null=True)
    colegio = models.CharField(max_length=200, blank=True, null=True)
    n_colegiado = models.CharField(max_length=200, blank=True, null=True)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    observaciones = models.CharField(max_length=200, blank=True, null=True)
    deshabilitar_domiciliacion = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.username
    
    class Meta:
            db_table = 'user'
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    