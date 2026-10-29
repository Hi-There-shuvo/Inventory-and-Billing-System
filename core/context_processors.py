from django.conf import settings
from .models import Product

LOW_STOCK_THRESHOLD = getattr(settings, 'LOW_STOCK_THRESHOLD', 3)


def low_stock_count(request):
    """Inject the count of low-stock products into every template context."""
    if request.user.is_authenticated and request.user.is_staff:
        count = Product.objects.filter(stock__lt=LOW_STOCK_THRESHOLD).count()
    else:
        count = 0
    return {'low_stock_count': count}
