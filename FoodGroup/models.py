from django.db import models

# Create your models here.
class FoodGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    users = models.ManyToManyField('Users.User') 

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'food_group'