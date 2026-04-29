from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    
    def __str__(self) -> str:
        return self.username
    
    class Meta:
            db_table = 'user'
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    