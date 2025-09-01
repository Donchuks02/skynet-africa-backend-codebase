from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ServiceInstance
from .serializers import ServiceInstanceSerializer
from .tasks import provision_service, restart_service, reinstall_service


# Create your views here.

class ServiceInstanceViewSet(viewsets.ModelViewSet):
    queryset = ServiceInstance.objects.all()
    serializer_class = ServiceInstanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ServiceInstance.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=["post"])
    def restart(self, request, pk=None):
        instance = self.get_object()
        restart_service.delay(instance.id)
        return Response({"status": "Service restart queued."})
    
    
    @action(detail=True, methods=["post"])
    def reinstall(self, request, pk=None):
        instance = self.get_object()
        reinstall_service.delay(instance.id)
        return Response({"status": "Service reinstall queued"})
