from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company_name', 'user', 'email', 'phone', 'is_archived', 'created_at')
    list_filter = ('is_archived', 'created_at', 'user')
    search_fields = ('full_name', 'company_name', 'email', 'phone')
