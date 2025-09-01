from celery import shared_task
from .models import ServiceInstance


@shared_task
def provision_service(service_instance_id):
    instance = ServiceInstance.objects.get(id=service_instance_id)
    # call cloud provider API here
    instance.status = "active"
    instance.save()
    return f"Provisioned service {instance.id}"


@shared_task
def restart_service(service_instance_id):
    instance = ServiceInstance.objects.get(id=service_instance_id)
    # call API to restart service
    return f"Restarted service {instance.id}"


@shared_task
def reinstall_service(service_instance_id):
    instance = ServiceInstance.objects.get(id=service_instance_id)
    # call API to reinstall
    return f"Reinstalled service {instance.id}"

