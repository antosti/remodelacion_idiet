from django.db import models
from Users.models import User
from Intakes.models import Intake
from Dishes.models import Dish
from Clients.models import Client

# Create your models here.

class Menu(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='menus', null=True, blank=True)
    date_ini = models.DateField()
    date_fin = models.DateField()
    
    # Many to many relationship with Intakes
    intake = models.ManyToManyField(Intake, through='MenuIntake')
    
    class Meta:
        db_table = 'menu'
        
class MenuIntake(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    kcal = models.DecimalField(max_digits=10, decimal_places=2)
    menu_day = models.IntegerField()
    intake_alias = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'menu_intake'