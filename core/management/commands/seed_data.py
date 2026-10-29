from django.core.management.base import BaseCommand
from core.models import Category, Product


SEED_DATA = {
    "Beverages": [
        {"name": "Mineral Water (500ml)", "price": "15.00", "stock": 150},
        {"name": "Coca-Cola (330ml)", "price": "35.00", "stock": 80},
        {"name": "Mango Juice (250ml)", "price": "25.00", "stock": 60},
        {"name": "Green Tea (250ml)", "price": "20.00", "stock": 45},
        {"name": "Energy Drink (250ml)", "price": "55.00", "stock": 30},
    ],
    "Snacks": [
        {"name": "Potato Chips (50g)", "price": "30.00", "stock": 100},
        {"name": "Chocolate Bar", "price": "45.00", "stock": 75},
        {"name": "Biscuits (200g)", "price": "40.00", "stock": 90},
        {"name": "Peanut Butter Cookies", "price": "60.00", "stock": 50},
        {"name": "Popcorn (Salted)", "price": "25.00", "stock": 65},
    ],
    "Dairy": [
        {"name": "Full Cream Milk (1L)", "price": "85.00", "stock": 40},
        {"name": "Plain Yogurt (200g)", "price": "30.00", "stock": 35},
        {"name": "Butter (100g)", "price": "70.00", "stock": 25},
        {"name": "Cheese Slice Pack", "price": "120.00", "stock": 20},
    ],
    "Household": [
        {"name": "Dish Soap (500ml)", "price": "55.00", "stock": 60},
        {"name": "Laundry Detergent (1kg)", "price": "130.00", "stock": 30},
        {"name": "Hand Sanitizer (100ml)", "price": "80.00", "stock": 45},
        {"name": "Toilet Paper (4 rolls)", "price": "90.00", "stock": 55},
    ],
    "Personal Care": [
        {"name": "Shampoo (200ml)", "price": "110.00", "stock": 40},
        {"name": "Toothpaste (100g)", "price": "65.00", "stock": 70},
        {"name": "Body Lotion (250ml)", "price": "150.00", "stock": 25},
        {"name": "Facewash (100ml)", "price": "95.00", "stock": 35},
    ],
}


class Command(BaseCommand):
    help = "Seed the database with dummy categories and products"

    def handle(self, *args, **kwargs):
        total_categories = 0
        total_products = 0

        for category_name, products in SEED_DATA.items():
            category, cat_created = Category.objects.get_or_create(name=category_name)
            if cat_created:
                total_categories += 1
                self.stdout.write(f"  [NEW] Category: {category_name}")
            else:
                self.stdout.write(f"  [OK]  Category exists: {category_name}")

            for item in products:
                product, prod_created = Product.objects.get_or_create(
                    name=item["name"],
                    defaults={
                        "category": category,
                        "price": item["price"],
                        "stock": item["stock"],
                    }
                )
                if prod_created:
                    total_products += 1
                    self.stdout.write(f"     + {product.name} (price: {product.price}, stock: {product.stock})")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {total_categories} categories and {total_products} products."
        ))
