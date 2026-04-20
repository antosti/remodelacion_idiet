from django.db import models
from Users.models import User
from Clients.models import Client

# Create your models here.

class Appointment(models.Model):
    
    STATUS = {
        'Cancelada': 'Cancelada',
        'Pendiente': 'Pendiente',
        'Confirmada': 'Confirmada'
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    motive = models.CharField(max_length=255, default='Consulta inicial')
    status = models.CharField(max_length=20, choices=STATUS, default='Pendiente')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    class Meta:
        db_table = 'appointment'