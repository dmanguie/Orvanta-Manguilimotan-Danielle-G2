from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class OrderType(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='order_types'
    )
    type_name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['type_name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'type_name'], name='unique_order_type_per_user')
        ]

    def __str__(self):
        return self.type_name


class Order(models.Model):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    READY = 'READY'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (READY, 'Ready'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    order_type = models.ForeignKey(
        OrderType,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    order_no = models.CharField(max_length=30)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    order_date = models.DateField(default=timezone.now)
    deadline = models.DateField(null=True, blank=True)
    fulfillment_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'order_no'], name='unique_order_no_per_user')
        ]

    def clean(self):
        super().clean()
        if self.deadline and self.order_date and self.deadline < self.order_date:
            raise ValidationError({'deadline': 'Deadline cannot be earlier than the order date.'})
        if self.fulfillment_date and self.order_date and self.fulfillment_date < self.order_date:
            raise ValidationError({'fulfillment_date': 'Fulfillment date cannot be earlier than the order date.'})

    def save(self, *args, **kwargs):
        if not self.order_no:
            year = (self.order_date or timezone.now().date()).year
            prefix = f"ORD-{year}-"
            last_order = Order.objects.filter(user=self.user, order_no__startswith=prefix).order_by('-order_no').first()
            if last_order:
                try:
                    last_num = int(last_order.order_no.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = Order.objects.filter(user=self.user).count() + 1
            else:
                next_num = 1
            self.order_no = f"{prefix}{next_num:04d}"

        if self.status == self.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != self.COMPLETED:
            self.completed_at = None

        super().save(*args, **kwargs)

    def recalculate_total(self):
        total = sum((item.line_total for item in self.items.all()), Decimal('0.00'))
        self.total_amount = total
        Order.objects.filter(pk=self.pk).update(total_amount=total)

    def __str__(self):
        return f"{self.order_no} - {self.title}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity <= Decimal('0'):
            raise ValidationError({'quantity': 'Quantity must be greater than zero.'})
        if self.unit_price is not None and self.unit_price < Decimal('0'):
            raise ValidationError({'unit_price': 'Unit price cannot be negative.'})

    def save(self, *args, **kwargs):
        qty = self.quantity or Decimal('0.00')
        price = self.unit_price or Decimal('0.00')
        self.line_total = qty * price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_description} ({self.quantity} @ ₱{self.unit_price})"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    remarks = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.order.order_no}: {self.old_status} -> {self.new_status}"
