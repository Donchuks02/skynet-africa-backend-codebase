from rest_framework import serializers
from .models import ServiceCredentials, ServiceInstance

class ServiceCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCredentials
        fields = ["email", "password", "ip_address", "port"]



class ServiceInstanceSerializer(serializers.ModelSerializer):
    credentials = ServiceCredentialsSerializer(read_only=True)
    class Meta:

        model = ServiceInstance

        fields = ["id","user", "order_id", "service_type", "instance_name", "configuration", "status", "created_at", "credentials"]

        read_only_fields = ["id", "user", "created_at", "credentials"]