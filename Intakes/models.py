from django.db import models

# Create your models here.

class Intake(models.Model):
    
    name = models.CharField(max_length=100)
    ingesta = models.CharField(max_length=100, default="")
    order = models.IntegerField()
    order_points = models.IntegerField(default=0)
    status = models.BooleanField(default=True)

    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'intake'