from django.db import models

# Create your models here.
class FoodGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    users = models.ManyToManyField('Users.User')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'food_group'


class FoodGroupExcluded(models.Model):
    client = models.ForeignKey('Clients.Client', on_delete=models.CASCADE, related_name='excluded_food_groups')
    food_group = models.ForeignKey(FoodGroup, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'food_group_excluded'
        unique_together = ('client', 'food_group')