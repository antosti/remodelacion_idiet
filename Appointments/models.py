from django.db import models
from Users.models import User
from Clients.models import Client

# Create your models here.

class Appointment(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    class Meta:
        db_table = 'appointment'