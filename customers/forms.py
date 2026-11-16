from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'company_name', 'email', 'phone', 'address', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'e.g. Maria Santos'}),
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g. Santos Crafts'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g. maria@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g. +63 912 345 6789'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Delivery or billing address'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Special preferences or notes'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = (cleaned_data.get('email') or '').strip()
        phone = (cleaned_data.get('phone') or '').strip()

        if not email and not phone:
            raise forms.ValidationError('A customer must have at least one contact detail (email or phone).')

        cleaned_data['email'] = email if email else None
        cleaned_data['phone'] = phone

        # Uniqueness check per user
        if email and self.user:
            qs = Customer.objects.filter(user=self.user, email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('email', 'A customer with this email address already exists in your account.')

        return cleaned_data
