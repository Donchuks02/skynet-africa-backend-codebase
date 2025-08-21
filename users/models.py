from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

# Create your models here. 


# This class handles the creation of user, the first method creates a regular user while the second method creates a superuser(admin).
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email) # make the provided email lowercase
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(email, password, **extra_fields)


# This class defines the custom user model that will be used in the application, this replaces the default user model that django provides.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    # This is constant defines which field will be used as a unique identifier for authentication
    USERNAME_FIELD = 'email'

    # the required field that must be provided when creating a superuser aside from the email.
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email