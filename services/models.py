from django.db import models
from django.conf import settings

# Create your models here.

class ServiceInstance(models.Model):
    SERVICES_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("terminated", "Terminated"),
        ("error", "Error"),

    ]

    user =  models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_instances")
    order_id = models.IntegerField
    service_type = models.CharField(max_length=50)
    instance_name = models.CharField(max_length=100, blank=True, null=True)
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=SERVICES_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.user} - {self.service_type}  ({self.status})"
    

class ServiceCredentials(models.Model):
    service_instance = models.OneToOneField(ServiceInstance, on_delete=models.CASCADE, related_name="credentials")
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    port = models.PositiveBigIntegerField(default=22)

    def __str__(self):
        return f"Credentials for {self.service_instance.instance_name or self.service_instance.id}"
