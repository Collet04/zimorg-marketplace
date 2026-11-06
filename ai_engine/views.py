from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from verification.models import EvidenceDocument


@login_required
def analysis_report_view(request, evidence_id):
    if not request.user.is_staff:
        raise PermissionDenied
    evidence = get_object_or_404(
        EvidenceDocument.objects.select_related('seller', 'seller__user'),
        pk=evidence_id,
    )
    return render(request, 'ai_engine/analysis_report.html', {
        'evidence': evidence,
        'audit_reasons': evidence.audit_reasons or evidence.screening_findings,
    })
