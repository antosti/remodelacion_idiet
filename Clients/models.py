from django.db import models
from Users.models import User
# Create your models here.

class Client(models.Model):
    
    GENDERS = {
        'Male': 'Male',
        'Female': 'Female'
    }
    
    ACTIVITY_LEVELS_CHOICES = {
        'Reposo': 'Reposo',
        'Ligera': 'Ligera',
        'Moderada': 'Moderada',
        'Intensa': 'Intensa'
    }
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDERS)
    height = models.IntegerField()
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    dni = models.CharField(max_length=15)
    phone_number = models.CharField(max_length=12)
    phone_number_2 = models.CharField(max_length=12)
    address = models.CharField(max_length=30)
    postal_code = models.CharField(max_length=10)
    city = models.CharField(max_length=50)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_LEVELS_CHOICES)
    
    class Meta:
        db_table = 'client'
    