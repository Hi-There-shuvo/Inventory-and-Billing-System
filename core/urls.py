from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:pk>/', views.product_delete, name='product_delete'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),

    # Billing
    path('billing/new/', views.billing_new, name='billing_new'),
    path('billing/invoice/<int:pk>/', views.invoice, name='invoice'),
    path('billing/history/', views.sale_history, name='sale_history'),

    # Inventory (Increment 2)
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/restock/<int:pk>/', views.restock, name='restock'),
    path('inventory/low-stock/', views.low_stock_alert, name='low_stock_alert'),

    # Users (Increment 3)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/delete/<int:pk>/', views.user_delete, name='user_delete'),
    path('users/change-password/', views.change_password, name='change_password'),

    # Reports (Increment 4)
    path('reports/daily/', views.report_daily, name='report_daily'),
    path('reports/top-products/', views.report_top_products, name='report_top_products'),
    path('reports/revenue/', views.report_revenue, name='report_revenue'),
]
