from django.db import models

# Create your models here.

class Intake(models.Model):

    class CourseRole(models.TextChoices):
        SINGLE = 'single', 'Único'
        STARTER = 'starter', 'Entrante'
        MAIN = 'main', 'Principal'
        DESSERT = 'dessert', 'Postre'

    name = models.CharField(max_length=100)
    ingesta = models.CharField(max_length=100, default="")
    order = models.IntegerField()
    order_points = models.IntegerField(default=0)
    status = models.BooleanField(default=True)
    course_role = models.CharField(max_length=10, choices=CourseRole.choices, default=CourseRole.SINGLE)
    meal_group = models.CharField(max_length=20, blank=True, default='')


    def __str__(self):
        return self.name

    class Meta:
        db_table = 'intake'