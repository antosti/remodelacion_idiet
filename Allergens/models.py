from django.db import models

# Create your models here.

class Allergen(models.Model):
    name = models.CharField(max_length=200)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'allergen'