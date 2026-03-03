from django.db import models
from Products.models import Product

# Create your models here.

class Dish(models.Model):
    
    name = models.CharField(max_length=200)
    recipe_elaboration = models.TextField(max_length=99999)
    language = models.CharField(max_length=50)
    
    # Many to many relationship with Products
    product = models.ManyToManyField(Product, through='DishProduct')
    
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