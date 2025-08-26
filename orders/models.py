from django.db import models
from django.conf import settings
import uuid
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

# Create your models here.

class Order(models.Model):
    
    STATUS_CHOICES = [
        ("draft", "Draft"),  
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),  
    ]

    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("one_time", "One Time"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="orders"
    )
    
    # Order identification number
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    

    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default="monthly")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    

    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Sum of all order items"
    )
    currency = models.CharField(max_length=3, default='NGN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    

    # This method runs every time an order is saved.
    # If the order is new and doesn't have a number yet, we create one.
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
            
        # We automatically set the 'confirmed' or 'completed' timestamps
        # when the status changes, so we don't have to do it manually.
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number: SKY-2025-000001
        This checks the last order from the current year to figure out the next number
        """
        year = timezone.now().year
        latest_order = Order.objects.filter(
            order_number__startswith=f'SKY-{year}-'
        ).order_by('-order_number').first()
        
        if latest_order:
            sequence = int(latest_order.order_number.split('-')[2]) + 1
        else:
            sequence = 1
        
        return f'SKY-{year}-{sequence:06d}'

    def calculate_subtotal(self):
        """Calculate subtotal from order items"""
        return sum(item.total_price for item in self.items.all())

    def update_subtotal(self):
        """Update and save the subtotal"""
        self.subtotal = self.calculate_subtotal()
        self.save(update_fields=['subtotal', 'updated_at'])

    @property
    def total_items(self):
        """Get total number of items in order"""
        return self.items.count()

    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['draft', 'pending']

    @property
    def is_ready_for_payment(self):
        """Check if order is ready for payment processing"""
        return self.status == 'pending' and self.items.exists()

    @property
    def is_provisioning_ready(self):
        """Check if order is ready for service provisioning"""
        return self.status == 'confirmed'










class OrderItem(models.Model):
    """Individual items within an order"""
    
    ITEM_TYPES = [
        ("shared_hosting", "Shared Hosting"),
        ("vps", "VPS"),
        ("gpu_vps", "GPU VPS"),
        ("dedicated_cloud", "Dedicated Cloud"),
        ("domain", "Domain Registration"),
        ("email", "Professional Email"),
        ("addon", "Service Addon"),
        ("setup_fee", "Setup Fee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Item identification
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    service_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Pricing (from service catalog)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Service configuration
    configuration = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Service-specific config: domain_name, hostname, os_template, etc."
    )
    
    # Reference to service catalog (for data integrity)
    service_plan_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="Reference to ServicePlan ID (loosely coupled)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.service_name}"

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)








class OrderStatusHistory(models.Model):
    """Track order status changes for auditing"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    

    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    
  
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number}: {self.previous_status} → {self.new_status}"


# Custom manager for common queries
class OrderManager(models.Manager):
    def pending_orders(self):
        return self.filter(status='pending')
    
    def user_orders(self, user):
        return self.filter(user=user)
    
    def ready_for_provisioning(self):
        return self.filter(status='confirmed')
    
    def active_orders(self):
        return self.exclude(status__in=['cancelled', 'completed', 'failed'])



Order.add_to_class('objects', OrderManager())

