from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Customer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customers',
        help_text='Owner/creator of this customer record'
    )
    full_name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'email'],
                name='unique_customer_email_per_user',
                condition=models.Q(email__isnull=False) & ~models.Q(email='')
            )
        ]

    def clean(self):
        super().clean()
        if not self.email and not self.phone:
            raise ValidationError('A customer must have at least one contact detail (email or phone).')

    def __str__(self):
        if self.company_name:
            return f"{self.full_name} ({self.company_name})"
        return self.full_name
