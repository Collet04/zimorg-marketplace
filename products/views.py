from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from sellers.models import SellerProfile
from .models import Product, Category
from .forms import ProductForm


def product_catalog_view(request):
    """Public marketplace product catalog with search and category filtering."""
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()

    products = Product.objects.filter(is_available=True).select_related('seller', 'category')
    categories = Category.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(seller__business_name__icontains=query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'query': query,
    }
    return render(request, 'products/catalog.html', context)


@login_required
def seller_product_list_view(request):
    """List products belonging to the logged-in seller."""
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')

    seller_profile = get_object_or_404(SellerProfile, user=request.user)
    products = seller_profile.products.all().order_by('-created_at')
    
    return render(request, 'products/seller_product_list.html', {'profile': seller_profile, 'products': products})


@login_required
def add_product_view(request):
    """Allow sellers to create new organic product listings."""
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')

    seller_profile = get_object_or_404(SellerProfile, user=request.user)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = seller_profile
            product.save()
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('products:seller_products')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ProductForm()

    return render(request, 'products/add_product.html', {'form': form, 'profile': seller_profile})