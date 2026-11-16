from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from customers.models import Customer
from .models import Order, OrderItem, OrderType


class OrderTypeForm(forms.ModelForm):
    class Meta:
        model = OrderType
        fields = ['type_name', 'description']
        widgets = {
            'type_name': forms.TextInput(attrs={'placeholder': 'e.g. Custom Furniture, Repair, Bulk Order'}),
            'description': forms.TextInput(attrs={'placeholder': 'Brief description of this order category'}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'order_type', 'title', 'description', 'order_date', 'deadline', 'fulfillment_date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Dining Table & 6 Chairs Set'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Detailed specifications, dimensions, materials, color...'}),
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'fulfillment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Internal notes or special handling'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['customer'].queryset = Customer.objects.filter(user=user, is_archived=False)
            self.fields['order_type'].queryset = OrderType.objects.filter(user=user, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        order_date = cleaned_data.get('order_date')
        deadline = cleaned_data.get('deadline')
        fulfillment_date = cleaned_data.get('fulfillment_date')

        if deadline and order_date and deadline < order_date:
            self.add_error('deadline', 'Deadline cannot be earlier than the order date.')

        if fulfillment_date and order_date and fulfillment_date < order_date:
            self.add_error('fulfillment_date', 'Fulfillment date cannot be earlier than the order date.')

        return cleaned_data


class BaseOrderItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        valid_items_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                desc = form.cleaned_data.get('item_description')
                qty = form.cleaned_data.get('quantity')
                price = form.cleaned_data.get('unit_price')
                if desc and qty and qty > 0:
                    valid_items_count += 1

        if valid_items_count < 1:
            raise forms.ValidationError('An order must have at least one line item (BR-21).')


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    fields=['item_description', 'quantity', 'unit_price'],
    extra=1,
    can_delete=True,
    formset=BaseOrderItemFormSet,
    widgets={
        'item_description': forms.TextInput(attrs={'placeholder': 'Item or service description'}),
        'quantity': forms.NumberInput(attrs={'step': '1', 'min': '1', 'placeholder': 'Qty'}),
        'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Price (₱)'}),
    }
)


class OrderStatusUpdateForm(forms.Form):
    new_status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    remarks = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Reason or note for this status change'})
    )
