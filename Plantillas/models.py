from django.db import models
from Users.models import User
from Intakes.models import Intake
from Dishes.models import Dish
from SuperGroup.models import SuperGroup
from django.core.validators import MinValueValidator
from django.db.models import F, Q

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


class Rule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rules')
    super_group = models.ForeignKey(
        SuperGroup,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    frequency = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    level = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f'{self.super_group} - nivel {self.level}'

    class Meta:
        db_table = 'rules'
        ordering = ['level', 'super_group__name', 'id']
        constraints = [
            models.CheckConstraint(
                condition=Q(min__lte=F('max')),
                name='rules_min_lte_max',
            ),
        ]
        indexes = [
            models.Index(fields=['user'], name='rules_user_idx'),
        ]
