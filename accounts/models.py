from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, phone_number, role, password=None):
        if not phone_number:
            raise ValueError("Phone number is required")
        user = self.model(phone_number=phone_number, role=role)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, role='admin'):
        user = self.model(phone_number=phone_number, role=role)
        user.set_password(password)
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    ROLE_CHOICES = (
        ('passenger', 'Passenger'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
    )

    phone_number = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.phone_number} ({self.role})"

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin
    

class DriverStatus(models.Model):
    driver = models.OneToOneField(User, on_delete=models.CASCADE)
    is_available = models.BooleanField(default=False)
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

class EmergencyContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50,  blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name}'s contact: {self.name} - {self.phone_number}"