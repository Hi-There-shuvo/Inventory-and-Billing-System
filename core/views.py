from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from .models import Product, Category, Sale, SaleItem
from .forms import ProductForm, CategoryForm, RestockForm, UserCreateForm, PasswordChangeForm

LOW_STOCK_THRESHOLD = getattr(settings, 'LOW_STOCK_THRESHOLD', 3)


# ─────────────────────────────────────────────────────────────
# Role Decorators
# ─────────────────────────────────────────────────────────────

def admin_required(view_func):
    """Restrict a view to Admin (is_staff) users only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, '🔒 Access denied. This section is for Admins only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    total_products = Product.objects.count()
    total_sales = Sale.objects.count()
    today = timezone.now().date()
    today_revenue = Sale.objects.filter(date__date=today).aggregate(
        total=Sum('total_amount'))['total'] or Decimal('0.00')
    low_stock_products = Product.objects.filter(stock__lt=LOW_STOCK_THRESHOLD)
    recent_sales = Sale.objects.order_by('-date')[:5]

    context = {
        'total_products': total_products,
        'total_sales': total_sales,
        'today_revenue': today_revenue,
        'low_stock_products': low_stock_products,
        'recent_sales': recent_sales,
    }
    return render(request, 'dashboard.html', context)


# ── Product Views ──

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.select_related('category').all()
    if query:
        products = products.filter(name__icontains=query)
    return render(request, 'products/product_list.html', {'products': products, 'query': query})


@admin_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product added successfully.')
        return redirect('product_list')
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Add Product'})


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product updated successfully.')
        return redirect('product_list')
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Edit Product'})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


# ── Category Views (Admin only) ──

@admin_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('product')).order_by('name')
    return render(request, 'products/category_list.html', {'categories': categories})


@admin_required
def category_add(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Category added successfully.')
        return redirect('category_list')
    return render(request, 'products/category_form.html', {'form': form, 'title': 'Add Category'})


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('category_list')
    return render(request, 'products/category_form.html', {'form': form, 'title': 'Edit Category'})


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted.')
        return redirect('category_list')
    return render(request, 'products/category_confirm_delete.html', {'category': category})


# ── Billing Views ──

@login_required
def billing_new(request):
    products = Product.objects.filter(stock__gt=0)
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', 'Walk-in Customer').strip() or 'Walk-in Customer'
        product_ids = request.POST.getlist('product_id')
        quantities  = request.POST.getlist('quantity')

        # ── Step 1: Build a validated list of (product, qty) BEFORE touching the DB ──
        validated_items = []
        has_error = False

        for pid, qty_str in zip(product_ids, quantities):
            try:
                qty = int(qty_str)
            except (ValueError, TypeError):
                continue
            if qty <= 0:
                continue  # skip unselected rows

            product = get_object_or_404(Product, pk=pid)
            if qty > product.stock:
                messages.error(
                    request,
                    f'Not enough stock for "{product.name}". '
                    f'Requested: {qty}, Available: {product.stock}'
                )
                has_error = True
                break  # stop on first error — no partial DB writes yet
            validated_items.append((product, qty))

        if has_error:
            return render(request, 'billing/billing_new.html', {'products': products})

        if not validated_items:
            messages.error(request, 'Please add at least one product to the bill.')
            return render(request, 'billing/billing_new.html', {'products': products})

        # ── Step 2: All clear — now create the Sale and SaleItems atomically ──
        from django.db import transaction
        with transaction.atomic():
            sale = Sale.objects.create(
                customer_name=customer_name,
                staff=request.user,
                total_amount=Decimal('0.00')
            )
            total = Decimal('0.00')
            for product, qty in validated_items:
                subtotal = product.price * qty
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    product_name=product.name,   # snapshot name
                    quantity=qty,
                    unit_price=product.price,
                    subtotal=subtotal,
                )
                product.stock -= qty
                product.save()
                total += subtotal

            sale.total_amount = total
            sale.save()

        messages.success(request, f'Sale #{sale.id} completed successfully!')
        return redirect('invoice', pk=sale.pk)

    return render(request, 'billing/billing_new.html', {'products': products})


@login_required
def invoice(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('product').all()
    return render(request, 'billing/invoice.html', {'sale': sale, 'items': items})


@login_required
def sale_history(request):
    sales = Sale.objects.order_by('-date')
    return render(request, 'billing/sale_history.html', {'sales': sales})


# ─────────────────────────────────────────────────────────────
# Inventory Management — Admin only
# ─────────────────────────────────────────────────────────────

@admin_required
def inventory(request):
    products = Product.objects.select_related('category').order_by('stock')
    return render(request, 'inventory/inventory.html', {'products': products})


@admin_required
def low_stock_alert(request):
    """Dedicated page showing all low-stock / out-of-stock products with inline restock."""
    alert_products = Product.objects.select_related('category').filter(stock__lt=LOW_STOCK_THRESHOLD).order_by('stock')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity   = request.POST.get('quantity')
        product    = get_object_or_404(Product, pk=product_id)
        try:
            qty = int(quantity)
            if qty > 0:
                product.stock += qty
                product.save()
                messages.success(request, f'✅ Restocked "{product.name}" by {qty} units. New stock: {product.stock}')
            else:
                messages.error(request, 'Quantity must be a positive number.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity entered.')
        return redirect('low_stock_alert')

    return render(request, 'inventory/low_stock_alert.html', {'alert_products': alert_products})


@admin_required
def restock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = RestockForm(request.POST or None)
    if form.is_valid():
        qty = form.cleaned_data['quantity']
        product.stock += qty
        product.save()
        messages.success(request, f'Restocked {product.name} by {qty} units.')
        return redirect('inventory')
    return render(request, 'inventory/restock_form.html', {'form': form, 'product': product})


# ─────────────────────────────────────────────────────────────
# User Management — Admin only
# ─────────────────────────────────────────────────────────────

@admin_required
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})


@admin_required
def user_add(request):
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'User created successfully.')
        return redirect('user_list')
    return render(request, 'users/user_form.html', {'form': form})


@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted.')
        return redirect('user_list')
    return render(request, 'users/user_confirm_delete.html', {'user_obj': user})


@login_required
def change_password(request):
    """Allow any logged-in user to change their own password."""
    form = PasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        # Re-authenticate so the session isn't invalidated after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        messages.success(request, '✅ Password changed successfully.')
        return redirect('dashboard')
    return render(request, 'users/change_password.html', {'form': form})


# ─────────────────────────────────────────────────────────────
# Reports & Analytics — Admin only
# ─────────────────────────────────────────────────────────────

@admin_required
def report_daily(request):
    today = timezone.now().date()
    sales = Sale.objects.filter(date__date=today)
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_transactions = sales.count()
    return render(request, 'reports/report_daily.html', {
        'sales': sales,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'today': today,
    })


@admin_required
def report_top_products(request):
    top_products = SaleItem.objects.values(
        'product__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_qty')[:10]
    return render(request, 'reports/report_top_products.html', {'top_products': top_products})


@admin_required
def report_revenue(request):
    today = timezone.now().date()
    # Last 7 days
    weekly_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        rev = Sale.objects.filter(date__date=day).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        weekly_data.append({'date': day, 'revenue': rev})

    # Monthly summary for current year
    monthly_data = []
    for month in range(1, 13):
        rev = Sale.objects.filter(
            date__year=today.year, date__month=month
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        monthly_data.append({'month': month, 'revenue': rev})

    return render(request, 'reports/report_revenue.html', {
        'weekly_data': weekly_data,
        'monthly_data': monthly_data,
        'year': today.year,
    })
