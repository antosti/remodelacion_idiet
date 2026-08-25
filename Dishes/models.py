from django.db import models
from Products.models import Product
from Intakes.models import Intake
from Users.models import User

# Create your models here.

class DishCategory(models.Model):
    """Categoría de plato importada de recipe_type (ej. 'carnes', 'pescados').

    Se llama DishCategory (en vez de DishType) para no chocar con el enum
    Dish.DishType (entrante/principal/postre/unico), aunque la tabla física
    sigue llamándose dish_type.
    """

    group_name = models.CharField(max_length=255, blank=True)
    name_es = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    name_de = models.CharField(max_length=255, blank=True)
    name_el = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name_es

    class Meta:
        db_table = 'dish_type'


class DishCategorySize(models.Model):
    """Tamaño de ración (en gramos) para una DishCategory, importado de recipe_type_size."""

    class Size(models.TextChoices):
        XXS = 'XXS', 'XXS'
        XS = 'XS', 'XS'
        S = 'S', 'S'
        M = 'M', 'M'
        L = 'L', 'L'
        XL = 'XL', 'XL'

    dish_category = models.ForeignKey(DishCategory, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=3, choices=Size.choices)
    quantity = models.DecimalField(max_digits=6, decimal_places=1)

    def __str__(self):
        return f"{self.dish_category} - {self.size}"

    class Meta:
        db_table = 'dish_type_size'


class Dish(models.Model):

    class DishType(models.TextChoices):
        STARTER = 'entrante', 'Entrante'
        MAIN = 'principal', 'Plato principal'
        DESSERT = 'postre', 'Postre'
        SINGLE = 'unico', 'Plato único'

    name = models.CharField(max_length=200)
    recipe_elaboration = models.TextField(max_length=99999)
    language = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    dish_type = models.CharField(max_length=10, choices=DishType.choices, default=DishType.MAIN)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    dish_category = models.ForeignKey(
        DishCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='dishes'
    )
    dish_category_size = models.ForeignKey(
        DishCategorySize, on_delete=models.SET_NULL, null=True, blank=True, related_name='dishes'
    )

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