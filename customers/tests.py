from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from .models import Customer


class CustomerManagementTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='owner1',
            email='owner1@example.com',
            password='Password123!',
            role=User.OWNER,
            business_name='Owner 1 Crafts'
        )
        self.owner2 = User.objects.create_user(
            username='owner2',
            email='owner2@example.com',
            password='Password123!',
            role=User.OWNER,
            business_name='Owner 2 Solutions'
        )
        self.client = Client()

    def test_customer_creation_requires_email_or_phone(self):
        self.client.login(username='owner1', password='Password123!')
        response = self.client.post(reverse('customer_create'), {
            'full_name': 'Test Customer',
            'company_name': 'Test Corp',
            'email': '',
            'phone': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'at least one contact detail')
        self.assertEqual(Customer.objects.count(), 0)

    def test_customer_creation_success(self):
        self.client.login(username='owner1', password='Password123!')
        response = self.client.post(reverse('customer_create'), {
            'full_name': 'Maria Santos',
            'company_name': 'Santos Woodworks',
            'email': 'maria@santos.com',
            'phone': '09123456789',
            'address': 'Cebu City',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Customer.objects.count(), 1)
        cust = Customer.objects.first()
        self.assertEqual(cust.user, self.owner1)
        self.assertEqual(cust.full_name, 'Maria Santos')

    def test_customer_isolation_between_users(self):
        # Create customer under owner1
        c1 = Customer.objects.create(
            user=self.owner1,
            full_name='Owner 1 Client',
            email='client1@test.com'
        )
        # Login as owner2
        self.client.login(username='owner2', password='Password123!')
        # Owner2 customer list should not show c1
        response = self.client.get(reverse('customer_list'))
        self.assertNotContains(response, 'Owner 1 Client')

        # Owner2 attempting to view c1 directly should return 404
        detail_response = self.client.get(reverse('customer_detail', args=[c1.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_customer_archive(self):
        c1 = Customer.objects.create(
            user=self.owner1,
            full_name='Archive Test',
            phone='123456'
        )
        self.client.login(username='owner1', password='Password123!')
        response = self.client.post(reverse('customer_delete', args=[c1.pk]), {'action_type': 'archive'})
        c1.refresh_from_db()
        self.assertTrue(c1.is_archived)
