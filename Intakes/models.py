from django.db import models

# Create your models here.

class Intake(models.Model):
    
    name = models.CharField(max_length=100)
    order = models.IntegerField()
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'intake'