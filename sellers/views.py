from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SellerProfile
from .forms import SellerProfileForm
from verification.models import mandatory_document_checklist, missing_mandatory_documents


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
            profile = form.save(commit=False)
            missing_documents = missing_mandatory_documents(profile)
            if missing_documents:
                profile.verification_status = SellerProfile.VerificationStatus.ADDITIONAL_EVIDENCE_REQUIRED
                profile.save()
                messages.warning(
                    request,
                    'Profile saved, but verification submission is blocked until these mandatory documents '
                    'are uploaded: ' + '; '.join(missing_documents),
                )
            else:
                profile.verification_status = SellerProfile.VerificationStatus.PENDING
                profile.save()
                messages.success(request, "Your seller profile and verification application have been submitted.")
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
    return render(request, 'sellers/dashboard.html', {
        'profile': profile,
        'mandatory_document_checklist': mandatory_document_checklist(profile),
    })