import json
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order


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
        history = instance.status_history or []
        history.append({
            "from": old_instance.status,
            "to": instance.status,
            "changed_at": timezone.now().isoformat(),
        })
        instance.status_history = history


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
