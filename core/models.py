from django.db import models
from django.conf import settings


LOW_STOCK_THRESHOLD = getattr(settings, 'LOW_STOCK_THRESHOLD', 3)


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock < LOW_STOCK_THRESHOLD


class Sale(models.Model):
    customer_name = models.CharField(max_length=200, blank=True, default='Walk-in Customer')
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales',
        verbose_name='Served by'
    )
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Sale #{self.id} - {self.customer_name}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,  # Keep sale history even if product is deleted
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=200, default='')  # snapshot at time of sale
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        # Snapshot the product name so it survives product deletion
        if self.product and not self.product_name:
            self.product_name = self.product.name
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def get_product_name(self):
        """Return product name from snapshot if product was deleted."""
        return self.product_name or (self.product.name if self.product else '(Deleted Product)')

    def __str__(self):
        return f"{self.get_product_name()} x {self.quantity}"
