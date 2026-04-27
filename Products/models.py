from django.db import models
from Micronutrients.models import Micronutrient
from FoodGroup.models import FoodGroup
from SuperGroup.models import SuperGroup

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
    food_group = models.ForeignKey(FoodGroup, on_delete=models.SET_NULL, null=True, blank=True)
    super_groups = models.ManyToManyField(SuperGroup, blank=True)

    # Many to many relationship with Micronutrient
    micronutrients = models.ManyToManyField(
        Micronutrient, 
        through='ProductMicronutrient'
    )
    
    def __str__(self) -> str:
        return self.food_name
    
    class Meta:
        db_table = 'product'

class ProductMicronutrient(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    micronutrient = models.ForeignKey(Micronutrient, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'product_micronutrient'
        unique_together = ('product', 'micronutrient')