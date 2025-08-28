from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from .models import ServiceInstance
from .tasks import provision_service


@receiver(post_save, sender=Order)
def create_service_instance(sender, instance, created, **kwargs):
    """
    Auto-create a ServiceInstance once an Order is marked as 'paid'
    """
    if instance.status == "paid" and not ServiceInstance.objects.filter(order_id=instance.id).exists():
        service_instance = ServiceInstance.objects.create(
            user=instance.user,
            order_id=instance.id,
            service_type=instance.orderitem.service_type,
            configuration=instance.orderitem.configuration,
        )
        provision_service.delay(service_instance.id)
