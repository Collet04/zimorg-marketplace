from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SellerProfile
from .forms import SellerProfileForm


@login_required
def seller_onboarding_view(request):
    # Restrict to sellers only based on our user role architecture
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')

    # Check if a profile already exists
    profile, created = SellerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = SellerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your seller profile and verification application details have been saved!")
            return redirect('sellers:dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SellerProfileForm(instance=profile)

    return render(request, 'sellers/onboarding.html', {'form': form, 'profile': profile})


@login_required
def seller_dashboard_view(request):
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')

    profile, created = SellerProfile.objects.get_or_create(user=request.user)
    return render(request, 'sellers/dashboard.html', {'profile': profile})