from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Category, Product, Sale, SaleItem, LOW_STOCK_THRESHOLD


class ModelTests(TestCase):
    """Test model behavior, methods, and properties."""

    def setUp(self):
        self.category = Category.objects.create(name="Beverages")
        self.product = Product.objects.create(
            name="Mineral Water",
            category=self.category,
            price=Decimal("25.00"),
            stock=10
        )

    def test_category_string_representation(self):
        self.assertEqual(str(self.category), "Beverages")

    def test_product_string_representation(self):
        self.assertEqual(str(self.product), "Mineral Water")

    def test_product_low_stock_property(self):
        # Stock >= LOW_STOCK_THRESHOLD should be False
        self.product.stock = LOW_STOCK_THRESHOLD
        self.product.save()
        self.assertFalse(self.product.is_low_stock)

        # Stock < LOW_STOCK_THRESHOLD should be True
        self.product.stock = LOW_STOCK_THRESHOLD - 1
        self.product.save()
        self.assertTrue(self.product.is_low_stock)

    def test_sale_item_subtotal_and_name_snapshot(self):
        user = User.objects.create_user(username="staff1", password="password123")
        sale = Sale.objects.create(customer_name="Alice", staff=user, total_amount=Decimal("50.00"))
        item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            subtotal=Decimal("0.00")
        )

        # Subtotal should be calculated automatically on save
        self.assertEqual(item.subtotal, Decimal("50.00"))
        # Product name snapshot should be preserved
        self.assertEqual(item.product_name, "Mineral Water")
        self.assertEqual(item.get_product_name(), "Mineral Water")

    def test_sale_item_preserves_history_when_product_is_deleted(self):
        """Bug #2 test: SaleItem should not be cascade deleted when Product is deleted."""
        user = User.objects.create_user(username="staff2", password="password123")
        sale = Sale.objects.create(customer_name="Bob", staff=user, total_amount=Decimal("25.00"))
        item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            subtotal=Decimal("0.00")
        )

        # Delete product
        self.product.delete()

        # Item and Sale should still exist
        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, "Mineral Water")
        self.assertEqual(item.get_product_name(), "Mineral Water")


class BillingAndCheckoutTests(TestCase):
    """Test point-of-sale billing, atomic deduction, and error handling."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="cashier", password="password123")
        self.client.login(username="cashier", password="password123")

        self.category = Category.objects.create(name="Snacks")
        self.product1 = Product.objects.create(
            name="Chips", category=self.category, price=Decimal("30.00"), stock=15
        )
        self.product2 = Product.objects.create(
            name="Cookies", category=self.category, price=Decimal("50.00"), stock=5
        )

    def test_successful_sale_and_stock_deduction(self):
        payload = {
            'customer_name': 'Hasan Ali',
            'product_id': [str(self.product1.pk), str(self.product2.pk)],
            'quantity': ['2', '1']
        }
        response = self.client.post(reverse('billing_new'), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        # Product stocks must be properly deducted
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, 13)
        self.assertEqual(self.product2.stock, 4)

        # Sale record verified
        sale = Sale.objects.get(customer_name='Hasan Ali')
        # Total: (2 * 30.00) + (1 * 50.00) = 110.00
        self.assertEqual(sale.total_amount, Decimal("110.00"))
        self.assertEqual(sale.items.count(), 2)

    def test_insufficient_stock_prevents_sale_creation(self):
        """Bug #1 test: Ensure no ghost sale is created if requested quantity > stock."""
        payload = {
            'customer_name': 'Overbuyer',
            'product_id': [str(self.product2.pk)],
            'quantity': ['10']  # Only 5 in stock!
        }
        response = self.client.post(reverse('billing_new'), payload)
        self.assertEqual(response.status_code, 200)

        # No sale should exist
        self.assertEqual(Sale.objects.filter(customer_name='Overbuyer').count(), 0)

        # Stock should remain untouched
        self.product2.refresh_from_db()
        self.assertEqual(self.product2.stock, 5)

    def test_empty_quantity_submission_rejected(self):
        payload = {
            'customer_name': 'No Items',
            'product_id': [str(self.product1.pk)],
            'quantity': ['0']
        }
        response = self.client.post(reverse('billing_new'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)

    def test_invoice_view_accessible(self):
        sale = Sale.objects.create(customer_name='Jane', staff=self.staff_user, total_amount=Decimal('30.00'))
        SaleItem.objects.create(
            sale=sale, product=self.product1, quantity=1, unit_price=Decimal('30.00'), subtotal=Decimal('30.00')
        )
        response = self.client.get(reverse('invoice', args=[sale.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane')
        self.assertContains(response, 'Chips')


class LowStockAlertAndInventoryTests(TestCase):
    """Test low stock identification, alert views, context processor, and restocking."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username="admin", password="password123")
        self.staff_user = User.objects.create_user(username="staff", password="password123")

        self.category = Category.objects.create(name="Dairy")
        self.low_product = Product.objects.create(
            name="Milk 1L", category=self.category, price=Decimal("90.00"), stock=1
        )
        self.normal_product = Product.objects.create(
            name="Butter 200g", category=self.category, price=Decimal("150.00"), stock=20
        )

    def test_context_processor_low_stock_count(self):
        # Admin user should see count = 1
        self.client.login(username="admin", password="password123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['low_stock_count'], 1)

        # Staff user should see 0 because staff doesn't manage inventory alerts
        self.client.login(username="staff", password="password123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['low_stock_count'], 0)

    def test_low_stock_alert_view_lists_depleted_items(self):
        self.client.login(username="admin", password="password123")
        response = self.client.get(reverse('low_stock_alert'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Milk 1L")
        self.assertNotContains(response, "Butter 200g")

    def test_inline_restock_on_low_stock_page(self):
        self.client.login(username="admin", password="password123")
        payload = {
            'product_id': self.low_product.pk,
            'quantity': 15
        }
        response = self.client.post(reverse('low_stock_alert'), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        # Stock should be updated: 1 + 15 = 16
        self.low_product.refresh_from_db()
        self.assertEqual(self.low_product.stock, 16)
        self.assertFalse(self.low_product.is_low_stock)


class RoleBasedAccessControlTests(TestCase):
    """Test RBAC restrictions between Admin and Staff users."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username="admin_user", password="password123")
        self.staff_user = User.objects.create_user(username="staff_user", password="password123")

    def test_staff_cannot_access_admin_inventory(self):
        self.client.login(username="staff_user", password="password123")
        response = self.client.get(reverse('inventory'))
        # Should redirect to dashboard with access denied
        self.assertRedirects(response, reverse('dashboard'))

    def test_staff_cannot_access_user_management(self):
        self.client.login(username="staff_user", password="password123")
        response = self.client.get(reverse('user_list'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_staff_cannot_access_reports(self):
        self.client.login(username="staff_user", password="password123")
        response = self.client.get(reverse('report_daily'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_can_access_all_management_views(self):
        self.client.login(username="admin_user", password="password123")
        for url_name in ['inventory', 'low_stock_alert', 'user_list', 'report_daily', 'report_revenue']:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    """Test user self-service password change functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="old_password_123")
        self.client.login(username="testuser", password="old_password_123")

    def test_password_change_success(self):
        payload = {
            'current_password': 'old_password_123',
            'new_password': 'new_secure_password_456',
            'confirm_password': 'new_secure_password_456'
        }
        response = self.client.post(reverse('change_password'), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        # Authenticate with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new_secure_password_456'))

    def test_password_change_fails_on_wrong_current_password(self):
        payload = {
            'current_password': 'wrong_password',
            'new_password': 'new_secure_password_456',
            'confirm_password': 'new_secure_password_456'
        }
        response = self.client.post(reverse('change_password'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'current_password', 'Current password is incorrect.')
