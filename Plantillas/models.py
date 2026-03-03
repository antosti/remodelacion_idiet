from django.db import models
from Users.models import User
from Intakes.models import Intake
from Dishes.models import Dish

# Create your models here.

class Template(models.Model):
    
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    daily_kcal = models.IntegerField()
    duration = models.IntegerField()
    
    # Many to many relationship with Intakes
    intake = models.ManyToManyField(Intake, through='TemplateIntake')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'template'
        
class TemplateIntake(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    kcal = models.DecimalField(max_digits=10, decimal_places=2)
    menu_day = models.IntegerField()
    intake_alias = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'template_intake'
    