from django.db import models
from Micronutrients.models import Micronutrient

# Create your models here.

class Product(models.Model):
    
    food_name = models.CharField(max_length=200, help_text="Original food name. Must be less than 200 characters")
    food_name_spanish = models.CharField(max_length=200)
    food_name_eng = models.CharField(max_length=200)
    origin_db = models.CharField(max_length=50)
    ed_porc = models.IntegerField()
    kcal_100g = models.IntegerField()
    prot_g = models.DecimalField(max_digits=10, decimal_places=2)
    ch_g = models.DecimalField(max_digits=10, decimal_places=2)
    fat_g = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Many to many relationship with Micronutrient
    micronutrient = models.ManyToManyField(Micronutrient)
    
    def __str__(self) -> str:
        return self.food_name
    
    class Meta:
        db_table = 'product'