from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from .forms import RegisterForm, ProfileForm
from .decorators import role_required
from .models import User


def redirect_by_role(user):
    return redirect('owner_dashboard' if user.role == User.OWNER else 'staff_dashboard')


def register_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect_by_role(user)
        messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    return redirect_by_role(request.user)


@role_required(User.OWNER)
def owner_dashboard(request):
    from orders.models import Order
    from customers.models import Customer
    from django.db.models import Sum

    user_orders = Order.objects.filter(user=request.user)
    stats = {
        'total_orders': user_orders.count(),
        'pending_orders': user_orders.filter(status=Order.PENDING).count(),
        'in_progress_orders': user_orders.filter(status=Order.IN_PROGRESS).count(),
        'completed_orders': user_orders.filter(status=Order.COMPLETED).count(),
        'total_revenue': user_orders.filter(status=Order.COMPLETED).aggregate(s=Sum('total_amount'))['s'] or 0,
        'total_customers': Customer.objects.filter(user=request.user, is_archived=False).count(),
    }
    recent_orders = user_orders.select_related('customer', 'order_type').order_by('-created_at')[:5]

    return render(request, 'accounts/owner_dashboard.html', {
        'stats': stats,
        'recent_orders': recent_orders,
        'total_users': User.objects.count(),
    })


@role_required(User.STAFF)
def staff_dashboard(request):
    from orders.models import Order

    user_orders = Order.objects.filter(user=request.user)
    stats = {
        'total_orders': user_orders.count(),
        'pending_orders': user_orders.filter(status=Order.PENDING).count(),
        'in_progress_orders': user_orders.filter(status=Order.IN_PROGRESS).count(),
        'ready_orders': user_orders.filter(status=Order.READY).count(),
    }
    recent_orders = user_orders.select_related('customer', 'order_type').order_by('-created_at')[:5]

    return render(request, 'accounts/staff_dashboard.html', {
        'stats': stats,
        'recent_orders': recent_orders,
    })


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/profile_edit.html', {'form': form})