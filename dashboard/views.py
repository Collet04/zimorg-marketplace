from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q

from auth_app.models import User
from sellers.models import SellerProfile
from verification.models import EvidenceDocument, mandatory_document_checklist, unapproved_mandatory_documents
from ai_engine.services import screen_evidence_document
from .decorators import admin_required
from .forms import CustomerAccountForm, EvidenceReviewForm, SellerVerificationForm


def _search(queryset, query, fields):
    if not query:
        return queryset

    criteria = Q()
    for field in fields:
        criteria |= Q(**{f'{field}__icontains': query})
    return queryset.filter(criteria)


@login_required
def admin_dashboard_home(request):
    if not request.user.is_staff:
        if request.user.is_admin_user():
            raise PermissionDenied
        if request.user.is_seller():
            return redirect('sellers:dashboard')
        return render(request, 'dashboard/home.html')

    verified_sellers = SellerProfile.objects.filter(
        verification_status=SellerProfile.VerificationStatus.VERIFIED,
    ).select_related('user').prefetch_related('evidence_documents').order_by('business_name')
    pending_statuses = (
        SellerProfile.VerificationStatus.PENDING,
        SellerProfile.VerificationStatus.UNDER_REVIEW,
        SellerProfile.VerificationStatus.ADDITIONAL_EVIDENCE_REQUIRED,
    )
    pending_sellers = SellerProfile.objects.filter(
        verification_status__in=pending_statuses,
    ).select_related('user').prefetch_related('evidence_documents').order_by('created_at')
    rejected_sellers = SellerProfile.objects.filter(
        verification_status=SellerProfile.VerificationStatus.REJECTED,
    ).select_related('user').prefetch_related('evidence_documents').order_by('-updated_at')

    return render(request, 'dashboard/admin_home.html', {
        'seller_count': SellerProfile.objects.count(),
        'customer_count': User.objects.filter(role=User.Role.BUYER).count(),
        'active_seller_count': verified_sellers.filter(user__is_active=True).count(),
        'pending_seller_count': pending_sellers.count(),
        'rejected_seller_count': rejected_sellers.count(),
        'verified_evidence_count': EvidenceDocument.objects.filter(
            status=EvidenceDocument.Status.ACCEPTED,
        ).count(),
        'evidence_review_count': EvidenceDocument.objects.filter(
            status__in=(
                EvidenceDocument.Status.UPLOADED,
                EvidenceDocument.Status.PROCESSING,
                EvidenceDocument.Status.PROCESSED,
                EvidenceDocument.Status.REQUIRES_REVIEW,
            ),
        ).count(),
        'verified_sellers': verified_sellers,
        'pending_sellers': pending_sellers,
        'rejected_sellers': rejected_sellers,
    })


home_view = admin_dashboard_home


@admin_required
def sellers_view(request):
    query = request.GET.get('q', '').strip()
    sellers = SellerProfile.objects.select_related('user').prefetch_related(
        'evidence_documents',
    ).order_by('business_name')
    sellers = _search(sellers, query, (
        'business_name',
        'user__email',
        'user__phone_number',
        'location',
    ))
    return render(request, 'dashboard/sellers.html', {
        'sellers': sellers,
        'query': query,
    })


@admin_required
def seller_detail_view(request, seller_id):
    seller = get_object_or_404(
        SellerProfile.objects.select_related('user').prefetch_related('evidence_documents'),
        pk=seller_id,
    )
    if request.method == 'POST':
        form = SellerVerificationForm(request.POST, instance=seller)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seller verification status updated.')
            return redirect('dashboard:seller_detail', seller_id=seller.pk)
    else:
        form = SellerVerificationForm(instance=seller)

    return render(request, 'dashboard/seller_detail.html', {
        'seller': seller,
        'documents': seller.evidence_documents.all().order_by('-created_at'),
        'mandatory_document_checklist': mandatory_document_checklist(seller),
        'verification_form': form,
    })


admin_seller_detail = seller_detail_view


@admin_required
@require_POST
def admin_verify_action(request, seller_id=None, evidence_id=None):
    action = request.POST.get('action', '').strip().lower()
    if action not in {'approve', 'reject'} or (seller_id is None) == (evidence_id is None):
        messages.error(request, 'Choose a valid approval or rejection action.')
        return redirect('dashboard:home')

    if seller_id is not None:
        seller = get_object_or_404(SellerProfile, pk=seller_id)
        if action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, 'A rejection reason is required.')
                return redirect('dashboard:seller_detail', seller_id=seller.pk)
            seller.verification_status = SellerProfile.VerificationStatus.REJECTED
            seller.rejection_reason = reason
        else:
            missing_approvals = unapproved_mandatory_documents(seller)
            if missing_approvals:
                messages.error(
                    request,
                    'Seller cannot be verified until all mandatory documents are approved: '
                    + '; '.join(missing_approvals),
                )
                return redirect('dashboard:seller_detail', seller_id=seller.pk)
            seller.verification_status = SellerProfile.VerificationStatus.VERIFIED
            seller.rejection_reason = ''
        seller.save(update_fields=['verification_status', 'rejection_reason', 'updated_at'])
        decision = 'approved' if action == 'approve' else 'rejected'
        messages.success(request, f'Seller application {decision}.')
        return redirect('dashboard:seller_detail', seller_id=seller.pk)

    evidence = get_object_or_404(EvidenceDocument, pk=evidence_id)
    review_notes = request.POST.get('review_notes', '').strip()
    if action == 'reject' and not review_notes:
        messages.error(request, 'A rejection reason is required.')
        return redirect('dashboard:evidence_detail', evidence_id=evidence.pk)
    evidence.status = (
        EvidenceDocument.Status.ACCEPTED
        if action == 'approve'
        else EvidenceDocument.Status.REJECTED
    )
    evidence.review_notes = review_notes
    evidence.reviewed_by = request.user
    evidence.save(update_fields=['status', 'review_notes', 'reviewed_by', 'updated_at'])
    decision = 'approved' if action == 'approve' else 'rejected'
    messages.success(request, f'Evidence document {decision}.')
    return redirect('dashboard:evidence_detail', evidence_id=evidence.pk)


@admin_required
def customers_view(request):
    query = request.GET.get('q', '').strip()
    customers = User.objects.filter(role=User.Role.BUYER).order_by('username')
    customers = _search(customers, query, (
        'username',
        'email',
        'first_name',
        'last_name',
        'phone_number',
    ))
    return render(request, 'dashboard/customers.html', {
        'customers': customers,
        'query': query,
    })


@admin_required
def customer_detail_view(request, customer_id):
    customer = get_object_or_404(User, pk=customer_id, role=User.Role.BUYER)
    if request.method == 'POST':
        form = CustomerAccountForm(request.POST)
        if form.is_valid():
            customer.is_active = form.cleaned_data['is_active']
            customer.save(update_fields=['is_active', 'updated_at'])
            messages.success(request, 'Customer account status updated.')
            return redirect('dashboard:customer_detail', customer_id=customer.pk)
    else:
        form = CustomerAccountForm(initial={'is_active': customer.is_active})

    return render(request, 'dashboard/customer_detail.html', {
        'customer': customer,
        'account_form': form,
    })


@admin_required
def evidence_view(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    screening_status = request.GET.get('screening_status', '').strip()
    documents = EvidenceDocument.objects.select_related(
        'seller',
        'seller__user',
        'reviewed_by',
    ).order_by('-created_at')
    valid_statuses = {choice[0] for choice in EvidenceDocument.Status.choices}
    if status in valid_statuses:
        documents = documents.filter(status=status)
    valid_screening_statuses = {choice[0] for choice in EvidenceDocument.ScreeningStatus.choices}
    if screening_status in valid_screening_statuses:
        documents = documents.filter(screening_status=screening_status)
    documents = _search(documents, query, (
        'title',
        'seller__business_name',
        'seller__user__email',
        'extracted_text',
    ))
    return render(request, 'dashboard/evidence.html', {
        'documents': documents,
        'query': query,
        'status': status,
        'statuses': EvidenceDocument.Status.choices,
        'screening_status': screening_status,
        'screening_statuses': EvidenceDocument.ScreeningStatus.choices,
    })


@admin_required
def evidence_detail_view(request, evidence_id):
    evidence = get_object_or_404(
        EvidenceDocument.objects.select_related('seller', 'seller__user', 'reviewed_by'),
        pk=evidence_id,
    )
    if request.method == 'POST':
        form = EvidenceReviewForm(request.POST, instance=evidence)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.reviewed_by = request.user
            evidence.save()
            messages.success(request, 'Document review saved.')
            return redirect('dashboard:evidence_detail', evidence_id=evidence.pk)
    else:
        form = EvidenceReviewForm(instance=evidence)

    return render(request, 'dashboard/evidence_detail.html', {
        'evidence': evidence,
        'review_form': form,
    })


@admin_required
@require_POST
def rescreen_evidence_view(request, evidence_id):
    evidence = get_object_or_404(EvidenceDocument, pk=evidence_id)
    screen_evidence_document(evidence)
    if evidence.screening_status == EvidenceDocument.ScreeningStatus.FAILED:
        messages.warning(
            request,
            'Automated screening could not complete. Review the screening findings and document manually.',
        )
    else:
        messages.success(request, 'Document screening completed.')
    return redirect('dashboard:evidence_detail', evidence_id=evidence.pk)