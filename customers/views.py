from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .models import Customer
from .forms import CustomerForm


@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    show_archived = request.GET.get('archived') == '1'

    customers = Customer.objects.filter(user=request.user)
    if not show_archived:
        customers = customers.filter(is_archived=False)

    if query:
        customers = customers.filter(
            Q(full_name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    return render(request, 'customers/customer_list.html', {
        'customers': customers,
        'query': query,
        'show_archived': show_archived,
        'active_count': Customer.objects.filter(user=request.user, is_archived=False).count(),
        'archived_count': Customer.objects.filter(user=request.user, is_archived=True).count(),
    })


@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, user=request.user)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.full_name}" created successfully!')
            return redirect('customer_detail', pk=customer.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = CustomerForm(user=request.user)
    return render(request, 'customers/customer_form.html', {'form': form, 'action': 'Create Customer'})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
    return render(request, 'customers/customer_detail.html', {'customer': customer})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer "{customer.full_name}" updated successfully.')
            return redirect('customer_detail', pk=customer.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = CustomerForm(instance=customer, user=request.user)
    return render(request, 'customers/customer_form.html', {'form': form, 'action': 'Edit Customer', 'customer': customer})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'archive')
        if action_type == 'delete':
            # Check if customer has orders before hard deleting
            if hasattr(customer, 'orders') and customer.orders.exists():
                messages.error(request, 'Cannot delete this customer because they have existing orders. You can archive them instead.')
                return redirect('customer_detail', pk=customer.pk)
            customer.delete()
            messages.success(request, 'Customer deleted successfully.')
            return redirect('customer_list')
        else:
            customer.is_archived = not customer.is_archived
            customer.save()
            status_text = 'archived' if customer.is_archived else 'restored'
            messages.success(request, f'Customer "{customer.full_name}" has been {status_text}.')
            return redirect('customer_detail', pk=customer.pk)
    return render(request, 'customers/customer_confirm_delete.html', {'customer': customer})
