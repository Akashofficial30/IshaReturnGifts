from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from products.models import Product, Category, Cart
from orders.models import Order, OrderItem
from payments.models import Payment
from django.contrib.auth.models import User


def admin_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_staff)(view_func), login_url='/dashboard/login/')


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─── AUTH ───────────────────────────────────────────────
def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('dashboard_home')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    return render(request, 'dashboard/login.html')


def dashboard_logout(request):
    logout(request)
    return redirect('dashboard_login')


# ─── HOME / OVERVIEW ────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def dashboard_home(request):
    today = timezone.now().date()
    last_30 = timezone.now() - timedelta(days=30)
    last_7 = timezone.now() - timedelta(days=7)

    # Stats
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_products = Product.objects.filter(is_active=True).count()
    total_customers = User.objects.filter(is_staff=False).count()
    pending_orders = Order.objects.filter(order_status='pending').count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Order.objects.filter(created_at__date=today, payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0
    monthly_revenue = Order.objects.filter(created_at__gte=last_30, payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Recent orders
    recent_orders = Order.objects.select_related().prefetch_related('items').order_by('-created_at')[:8]

    # Low stock products
    low_stock = Product.objects.filter(stock_quantity__lte=10, is_active=True).order_by('stock_quantity')[:5]

    # Orders by status
    order_status_data = Order.objects.values('order_status').annotate(count=Count('id'))

    # Revenue last 7 days (for chart)
    revenue_chart = []
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        rev = Order.objects.filter(
            created_at__date=day.date(),
            payment_status='paid'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        revenue_chart.append({'day': day.strftime('%a'), 'revenue': float(rev)})

    # Top selling products
    top_products = OrderItem.objects.values('product_name').annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('product_price')
    ).order_by('-total_qty')[:5]

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_customers': total_customers,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'recent_orders': recent_orders,
        'low_stock': low_stock,
        'order_status_data': list(order_status_data),
        'revenue_chart': revenue_chart,
        'top_products': top_products,
    }
    return render(request, 'dashboard/home.html', context)


# ─── ORDERS ─────────────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def order_list(request):
    orders = Order.objects.prefetch_related('items').order_by('-created_at')

    # Filters
    status = request.GET.get('status', '')
    payment = request.GET.get('payment', '')
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status:
        orders = orders.filter(order_status=status)
    if payment:
        orders = orders.filter(payment_status=payment)
    if search:
        orders = orders.filter(
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search) |
            Q(payment_id__icontains=search)
        )
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    context = {
        'orders': orders,
        'status_filter': status,
        'payment_filter': payment,
        'search': search,
        'total_count': orders.count(),
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'dashboard/orders.html', context)


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        order_status = request.POST.get('order_status')
        payment_status = request.POST.get('payment_status')
        notes = request.POST.get('notes', '')
        if order_status:
            order.order_status = order_status
        if payment_status:
            order.payment_status = payment_status
        order.notes = notes
        order.save()
        messages.success(request, f'Order #{order.get_short_order_id()} updated successfully.')
        return redirect('dashboard_order_detail', order_id=order.id)
    return render(request, 'dashboard/order_detail.html', {'order': order})


# ─── PRODUCTS ───────────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def product_list(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    stock = request.GET.get('stock', '')

    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category:
        products = products.filter(category__slug=category)
    if stock == 'low':
        products = products.filter(stock_quantity__lte=10)
    elif stock == 'out':
        products = products.filter(stock_quantity=0)

    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
        'search': search,
        'category_filter': category,
        'stock_filter': stock,
    }
    return render(request, 'dashboard/products.html', context)


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def product_add(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        from django.utils.text import slugify
        name = request.POST.get('name')
        slug = slugify(name)
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            name=name,
            slug=slug,
            category_id=request.POST.get('category'),
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            offer_price=request.POST.get('offer_price') or None,
            stock_quantity=request.POST.get('stock_quantity', 0),
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active') == 'on',
        )
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        messages.success(request, f'Product "{name}" added successfully!')
        return redirect('dashboard_products')
    return render(request, 'dashboard/product_form.html', {'categories': categories, 'action': 'Add'})


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.offer_price = request.POST.get('offer_price') or None
        product.stock_quantity = request.POST.get('stock_quantity', 0)
        product.is_featured = request.POST.get('is_featured') == 'on'
        product.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        messages.success(request, f'Product "{product.name}" updated successfully!')
        return redirect('dashboard_products')
    return render(request, 'dashboard/product_form.html', {'product': product, 'categories': categories, 'action': 'Edit'})


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect('dashboard_products')
    return render(request, 'dashboard/confirm_delete.html', {'object': product, 'type': 'Product'})


# ─── CATEGORIES ─────────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'dashboard/categories.html', {'categories': categories})


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def category_add(request):
    if request.method == 'POST':
        from django.utils.text import slugify
        name = request.POST.get('name')
        slug = slugify(name)
        base_slug = slug
        counter = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        cat = Category(name=name, slug=slug, description=request.POST.get('description', ''))
        if request.FILES.get('image'):
            cat.image = request.FILES['image']
        cat.save()
        messages.success(request, f'Category "{name}" added!')
        return redirect('dashboard_categories')
    return render(request, 'dashboard/category_form.html', {'action': 'Add'})


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def category_edit(request, cat_id):
    category = get_object_or_404(Category, id=cat_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description', '')
        if request.FILES.get('image'):
            category.image = request.FILES['image']
        category.save()
        messages.success(request, f'Category updated!')
        return redirect('dashboard_categories')
    return render(request, 'dashboard/category_form.html', {'category': category, 'action': 'Edit'})


@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def category_delete(request, cat_id):
    category = get_object_or_404(Category, id=cat_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted.')
        return redirect('dashboard_categories')
    return render(request, 'dashboard/confirm_delete.html', {'object': category, 'type': 'Category'})


# ─── CUSTOMERS ──────────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def customer_list(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )
    # Annotate with order count
    customer_data = []
    for c in customers:
        orders = Order.objects.filter(customer_email=c.email)
        customer_data.append({
            'user': c,
            'order_count': orders.count(),
            'total_spent': orders.filter(payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        })
    return render(request, 'dashboard/customers.html', {'customer_data': customer_data, 'search': search})


# ─── PAYMENTS ───────────────────────────────────────────
@login_required(login_url='/dashboard/login/')
@user_passes_test(is_admin, login_url='/dashboard/login/')
def payment_list(request):
    payments = Payment.objects.select_related('order').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        payments = payments.filter(status=status)
    total_collected = payments.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'dashboard/payments.html', {
        'payments': payments,
        'status_filter': status,
        'total_collected': total_collected,
    })
