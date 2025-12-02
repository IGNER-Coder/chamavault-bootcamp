from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # We keep the default fields (username, email, password) from AbstractUser
    # and add our own:
    
    phone_number = models.CharField(max_length=15, unique=True)
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # This helps us identify them easily in the Admin panel
    def __str__(self):
        return f"{self.username} ({self.phone_number})"