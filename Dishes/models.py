from django.db import models
from Products.models import Product
from Intakes.models import Intake

# Create your models here.

class Dish(models.Model):
    
    name = models.CharField(max_length=200)
    recipe_elaboration = models.TextField(max_length=99999)
    language = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    
    # Many to many relationship with Products
    product = models.ManyToManyField(Product, through='DishProduct')
    # Many to many relationship with Intakes
    intakes = models.ManyToManyField(Intake, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'dish'
        
class DishProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    
    class Meta:
        db_table = 'dish_product'