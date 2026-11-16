from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from customers.models import Customer
from .models import Order, OrderItem, OrderType, OrderStatusHistory
from .forms import OrderForm, OrderItemFormSet, OrderStatusUpdateForm, OrderTypeForm


def ensure_default_order_type(user):
    order_type, _ = OrderType.objects.get_or_create(
        user=user,
        type_name='General',
        defaults={'description': 'Standard general order or service'}
    )
    return order_type


@login_required
def order_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()

    orders = Order.objects.filter(user=request.user).select_related('customer', 'order_type')

    if status_filter:
        orders = orders.filter(status=status_filter)

    if type_filter:
        orders = orders.filter(order_type_id=type_filter)

    if query:
        orders = orders.filter(
            Q(order_no__icontains=query) |
            Q(title__icontains=query) |
            Q(customer__full_name__icontains=query) |
            Q(customer__company_name__icontains=query)
        )

    all_user_orders = Order.objects.filter(user=request.user)
    stats = {
        'total': all_user_orders.count(),
        'pending': all_user_orders.filter(status=Order.PENDING).count(),
        'in_progress': all_user_orders.filter(status=Order.IN_PROGRESS).count(),
        'ready': all_user_orders.filter(status=Order.READY).count(),
        'completed': all_user_orders.filter(status=Order.COMPLETED).count(),
        'total_revenue': all_user_orders.filter(status=Order.COMPLETED).aggregate(s=Sum('total_amount'))['s'] or 0,
    }

    order_types = OrderType.objects.filter(user=request.user, is_active=True)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'query': query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'stats': stats,
        'order_types': order_types,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
    })


@login_required
def order_create(request):
    ensure_default_order_type(request.user)

    # Check if there is at least one active customer
    active_customers = Customer.objects.filter(user=request.user, is_archived=False)
    if not active_customers.exists():
        messages.warning(request, 'Please create a customer first before adding an order.')
        return redirect('customer_create')

    initial = {}
    customer_id = request.GET.get('customer')
    if customer_id:
        initial['customer'] = customer_id

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        formset = OrderItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.save()

                formset.instance = order
                formset.save()

                order.recalculate_total()

                # Audit log initial creation
                OrderStatusHistory.objects.create(
                    order=order,
                    changed_by=request.user,
                    old_status=None,
                    new_status=order.status,
                    remarks='Order created'
                )

            messages.success(request, f'Order {order.order_no} created successfully!')
            return redirect('order_detail', pk=order.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = OrderForm(user=request.user, initial=initial)
        formset = OrderItemFormSet()

    return render(request, 'orders/order_form.html', {
        'form': form,
        'formset': formset,
        'action': 'Create Order',
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('customer', 'order_type').prefetch_related('items', 'status_history__changed_by'),
        pk=pk,
        user=request.user
    )
    status_form = OrderStatusUpdateForm(initial={'new_status': order.status})

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'status_form': status_form,
    })


@login_required
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, user=request.user)
        formset = OrderItemFormSet(request.POST, instance=order)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                order.recalculate_total()
            messages.success(request, f'Order {order.order_no} updated successfully.')
            return redirect('order_detail', pk=order.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = OrderForm(instance=order, user=request.user)
        formset = OrderItemFormSet(instance=order)

    return render(request, 'orders/order_form.html', {
        'form': form,
        'formset': formset,
        'action': f'Edit Order {order.order_no}',
        'order': order,
    })


@login_required
def order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['new_status']
            remarks = form.cleaned_data.get('remarks', '').strip()

            if new_status != order.status:
                old_status = order.status
                order.status = new_status
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    changed_by=request.user,
                    old_status=old_status,
                    new_status=new_status,
                    remarks=remarks or f'Status updated to {order.get_status_display()}'
                )
                messages.success(request, f'Order status updated to {order.get_status_display()}.')
            else:
                messages.info(request, 'Status unchanged.')
        else:
            messages.error(request, 'Invalid status selection.')

    return redirect('order_detail', pk=order.pk)


@login_required
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    # Role check: only owner can permanently delete
    is_owner = request.user.role == 'owner' or request.user.is_superuser

    if request.method == 'POST':
        action = request.POST.get('action', 'cancel')

        if action == 'delete':
            if not is_owner:
                messages.error(request, 'Only business owners can delete order records.')
                return redirect('order_detail', pk=order.pk)

            order_no = order.order_no
            order.delete()
            messages.success(request, f'Order {order_no} deleted successfully.')
            return redirect('order_list')
        else:
            old_status = order.status
            order.status = Order.CANCELLED
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                changed_by=request.user,
                old_status=old_status,
                new_status=Order.CANCELLED,
                remarks=request.POST.get('remarks', 'Cancelled by user')
            )
            messages.success(request, f'Order {order.order_no} has been cancelled.')
            return redirect('order_detail', pk=order.pk)

    return render(request, 'orders/order_confirm_delete.html', {
        'order': order,
        'is_owner': is_owner,
    })


@login_required
def order_types_list(request):
    order_types = OrderType.objects.filter(user=request.user)
    if request.method == 'POST':
        form = OrderTypeForm(request.POST)
        if form.is_valid():
            ot = form.save(commit=False)
            ot.user = request.user
            ot.save()
            messages.success(request, f'Order Type "{ot.type_name}" added!')
            return redirect('order_types_list')
        messages.error(request, 'Please correct the error.')
    else:
        form = OrderTypeForm()

    return render(request, 'orders/order_types_list.html', {
        'order_types': order_types,
        'form': form,
    })
