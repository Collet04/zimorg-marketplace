from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from sellers.models import SellerProfile
from .models import EvidenceDocument
from .forms import EvidenceUploadForm
from ai_engine.services import screen_evidence_document


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
        form = EvidenceUploadForm(request.POST, request.FILES, seller=seller_profile)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.seller = seller_profile
            evidence.status = EvidenceDocument.Status.REQUIRES_REVIEW
            evidence.save()
            screen_evidence_document(evidence)
            if evidence.screening_status == EvidenceDocument.ScreeningStatus.FAILED:
                messages.warning(
                    request,
                    "Document uploaded. Automated screening could not complete; a verifier must review it manually.",
                )
            else:
                messages.success(request, "Evidence document successfully uploaded and sent for review!")
            return redirect('verification:evidence_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EvidenceUploadForm(seller=seller_profile)

    return render(request, 'verification/upload_evidence.html', {
        'form': form,
        'profile': seller_profile,
        'is_update': False,
    })


@login_required
def update_evidence_view(request, evidence_id):
    if not request.user.is_seller():
        messages.error(request, "Access restricted to seller accounts.")
        return redirect('dashboard:home')

    seller_profile = get_object_or_404(SellerProfile, user=request.user)
    evidence = get_object_or_404(
        EvidenceDocument,
        pk=evidence_id,
        seller=seller_profile,
    )

    if request.method == 'POST':
        form = EvidenceUploadForm(
            request.POST,
            request.FILES,
            instance=evidence,
            seller=seller_profile,
        )
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.status = EvidenceDocument.Status.REQUIRES_REVIEW
            evidence.review_notes = ''
            evidence.reviewed_by = None
            evidence.extracted_text = ''
            evidence.screening_status = EvidenceDocument.ScreeningStatus.PENDING
            evidence.screening_recommendation = EvidenceDocument.ScreeningRecommendation.REVIEW
            evidence.screening_findings = []
            evidence.screened_at = None
            evidence.save()
            screen_evidence_document(evidence)
            if evidence.screening_status == EvidenceDocument.ScreeningStatus.FAILED:
                messages.warning(
                    request,
                    "Document updated. Automated screening could not complete; a verifier must review it manually.",
                )
            else:
                messages.success(request, "Evidence document updated and sent for review.")
            return redirect('verification:evidence_list')
        messages.error(request, "Please correct the errors below.")
    else:
        form = EvidenceUploadForm(instance=evidence, seller=seller_profile)

    return render(request, 'verification/upload_evidence.html', {
        'form': form,
        'profile': seller_profile,
        'is_update': True,
        'evidence': evidence,
    })