from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from sellers.models import SellerProfile
from .models import EvidenceDocument
from .forms import EvidenceUploadForm


@login_required
def evidence_list_view(request):
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')
    
    seller_profile = get_object_or_404(SellerProfile, user=request.user)
    documents = seller_profile.evidence_documents.all().order_by('-created_at')
    
    return render(request, 'verification/evidence_list.html', {'profile': seller_profile, 'documents': documents})


@login_required
def upload_evidence_view(request):
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')
    
    seller_profile = get_object_or_404(SellerProfile, user=request.user)

    if request.method == 'POST':
        form = EvidenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.seller = seller_profile
            evidence.status = EvidenceDocument.Status.REQUIRES_REVIEW
            evidence.save()
            messages.success(request, "Evidence document successfully uploaded and sent for review!")
            return redirect('verification:evidence_list')
        else:
            messages.error(request, "Please check your file upload details and try again.")
    else:
        form = EvidenceUploadForm()

    return render(request, 'verification/upload_evidence.html', {'form': form, 'profile': seller_profile})