from django.db.models.signals import post_save, post_delete
from .models import OrderItem
import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, OrderItem



# Update order subtotal when items change
@receiver([post_save, post_delete], sender=OrderItem)
def update_order_subtotal(sender, instance, **kwargs):
    """Update order subtotal when items change"""
    instance.order.update_subtotal()


@receiver(pre_save, sender=Order)
def track_status_change(sender, instance, **kwargs):
    """
    Before saving, if status has changed, append the change to status_history.
    """
    if not instance.pk:
        return

    try:
        old_instance = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if old_instance.status != instance.status:
        from .models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=instance,
            previous_status=old_instance.status,
            new_status=instance.status,
            reason="Status changed by signal"
        )


@receiver(post_save, sender=Order)
def ensure_initial_status(sender, instance, created, **kwargs):
    """
    If it's a brand new order, ensure status_history starts with initial status.
    """
    if created and not instance.status_history:
        instance.status_history = [{
            "from": None,
            "to": instance.status,
            "changed_at": timezone.now().isoformat(),
        }]
        instance.save(update_fields=["status_history"])
