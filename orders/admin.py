from django.contrib import admin
from .models import OrderType, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('changed_by', 'old_status', 'new_status', 'remarks', 'changed_at')
    can_delete = False


@admin.register(OrderType)
class OrderTypeAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'user', 'is_active', 'created_at')
    list_filter = ('is_active', 'user')
    search_fields = ('type_name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'title', 'user', 'customer', 'order_type', 'status', 'total_amount', 'order_date', 'deadline')
    list_filter = ('status', 'order_type', 'order_date', 'user')
    search_fields = ('order_no', 'title', 'customer__full_name')
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item_description', 'quantity', 'unit_price', 'line_total')
    search_fields = ('item_description', 'order__order_no')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'changed_by', 'old_status', 'new_status', 'changed_at')
    list_filter = ('new_status', 'changed_at')
