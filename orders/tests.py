from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from customers.models import Customer
from .models import Order, OrderItem, OrderType, OrderStatusHistory


class OrderCoreFeatureTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@test.com',
            password='Password123!',
            role=User.OWNER,
            business_name='Orvanta Test Business'
        )
        self.staff = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='Password123!',
            role=User.STAFF,
            business_name='Orvanta Test Business'
        )
        self.other_owner = User.objects.create_user(
            username='other_user',
            email='other@test.com',
            password='Password123!',
            role=User.OWNER,
            business_name='Other Store'
        )
        self.customer = Customer.objects.create(
            user=self.owner,
            full_name='Juan Dela Cruz',
            email='juan@example.com',
            phone='09181234567'
        )
        self.order_type = OrderType.objects.create(
            user=self.owner,
            type_name='Custom Furniture',
            description='Handmade wooden pieces'
        )
        self.client = Client()

    def test_order_creation_with_items_and_total_calculation(self):
        self.client.login(username='owner_user', password='Password123!')
        response = self.client.post(reverse('order_create'), {
            'customer': self.customer.pk,
            'order_type': self.order_type.pk,
            'title': 'Solid Mahogany Dining Table',
            'description': '6-seater dining table with varnished mahogany finish',
            'order_date': '2026-11-16',
            'deadline': '2026-11-30',
            'fulfillment_date': '2026-11-28',
            'notes': 'Deliver to Cebu City warehouse',
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item_description': 'Mahogany Dining Table',
            'items-0-quantity': '1',
            'items-0-unit_price': '25000.00',
            'items-1-item_description': 'Matching Dining Chair',
            'items-1-quantity': '6',
            'items-1-unit_price': '2500.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.user, self.owner)
        self.assertTrue(order.order_no.startswith('ORD-2026-'))
        self.assertEqual(order.items.count(), 2)
        # 25,000 + (6 * 2,500) = 40,000
        self.assertEqual(order.total_amount, Decimal('40000.00'))
        # Initial status history created
        self.assertEqual(order.status_history.count(), 1)
        self.assertEqual(order.status_history.first().new_status, Order.PENDING)

    def test_order_validation_deadline_cannot_be_before_order_date(self):
        self.client.login(username='owner_user', password='Password123!')
        response = self.client.post(reverse('order_create'), {
            'customer': self.customer.pk,
            'order_type': self.order_type.pk,
            'title': 'Invalid Date Order',
            'order_date': '2026-11-16',
            'deadline': '2026-11-10', # Before order date!
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item_description': 'Item 1',
            'items-0-quantity': '1',
            'items-0-unit_price': '100.00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deadline cannot be earlier than the order date')
        self.assertEqual(Order.objects.count(), 0)

    def test_order_status_workflow_and_audit_history(self):
        order = Order.objects.create(
            user=self.owner,
            customer=self.customer,
            order_type=self.order_type,
            title='Office Desk',
            order_date=timezone.now().date(),
            status=Order.PENDING
        )
        self.client.login(username='owner_user', password='Password123!')
        response = self.client.post(reverse('order_status_update', args=[order.pk]), {
            'new_status': Order.IN_PROGRESS,
            'remarks': 'Materials sourced, starting assembly',
        })
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.IN_PROGRESS)
        self.assertEqual(order.status_history.count(), 1)
        history_entry = order.status_history.first()
        self.assertEqual(history_entry.old_status, Order.PENDING)
        self.assertEqual(history_entry.new_status, Order.IN_PROGRESS)
        self.assertEqual(history_entry.remarks, 'Materials sourced, starting assembly')

    def test_user_data_isolation(self):
        # Order belongs to self.owner
        order = Order.objects.create(
            user=self.owner,
            customer=self.customer,
            order_type=self.order_type,
            title='Confidential Order',
            order_date=timezone.now().date(),
        )
        # Login as different business owner
        self.client.login(username='other_user', password='Password123!')
        list_response = self.client.get(reverse('order_list'))
        self.assertNotContains(list_response, 'Confidential Order')

        # Direct access to other user's order yields 404
        detail_response = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_staff_cannot_delete_order(self):
        order = Order.objects.create(
            user=self.staff,
            customer=self.customer,
            order_type=self.order_type,
            title='Staff Order',
            order_date=timezone.now().date(),
        )
        self.client.login(username='staff_user', password='Password123!')
        response = self.client.post(reverse('order_delete', args=[order.pk]), {'action': 'delete'})
        self.assertEqual(response.status_code, 302)
        # Order should not be deleted because user is staff
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
