from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('login/', views.dashboard_login, name='dashboard_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),

    # Orders
    path('orders/', views.order_list, name='dashboard_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='dashboard_order_detail'),

    # Products
    path('products/', views.product_list, name='dashboard_products'),
    path('products/add/', views.product_add, name='dashboard_product_add'),
    path('products/<int:product_id>/edit/', views.product_edit, name='dashboard_product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='dashboard_product_delete'),

    # Categories
    path('categories/', views.category_list, name='dashboard_categories'),
    path('categories/add/', views.category_add, name='dashboard_category_add'),
    path('categories/<int:cat_id>/edit/', views.category_edit, name='dashboard_category_edit'),
    path('categories/<int:cat_id>/delete/', views.category_delete, name='dashboard_category_delete'),

    # Customers
    path('customers/', views.customer_list, name='dashboard_customers'),

    # Payments
    path('payments/', views.payment_list, name='dashboard_payments'),
]
