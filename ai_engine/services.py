import io
import logging
import os
import re
import shutil
from datetime import date
from pathlib import Path

import pymupdf
from PIL import Image, UnidentifiedImageError
import pytesseract
from django.conf import settings
from django.utils import timezone

from verification.models import EvidenceDocument, missing_mandatory_documents

logger = logging.getLogger(__name__)

MAX_DOCUMENT_PAGES = 20
MIN_TEXT_LENGTH = 40

MARKETPLACE_TERMS = {
    'organic', 'organically', 'farm', 'farmer', 'farming', 'agriculture',
    'agricultural', 'crop', 'crops', 'produce', 'harvest', 'pesticide',
    'pesticides', 'pgs', 'participatory guarantee', 'zofa',
    'soil', 'compost', 'livestock', 'horticulture',
}

DOCUMENT_TYPE_TERMS = {
    EvidenceDocument.DocumentType.CERTIFICATE: {
        'certificate', 'certification', 'certified', 'organic', 'pgs',
        'participatory guarantee',
    },
    EvidenceDocument.DocumentType.PGS_RECORD: {
        'pgs', 'participatory guarantee', 'farmer group', 'peer review',
        'organic',
    },
    EvidenceDocument.DocumentType.INSPECTION_RECORD: {
        'inspection', 'inspector', 'audit', 'farm visit', 'organic', 'pgs',
    },
    EvidenceDocument.DocumentType.FARM_RECORD: {
        'farm', 'production', 'planting', 'harvest', 'crop', 'field',
        'organic',
    },
    EvidenceDocument.DocumentType.INPUT_RECORD: {
        'soil', 'input', 'compost', 'fertilizer', 'fertiliser', 'seed',
        'pesticide', 'farm',
    },
    EvidenceDocument.DocumentType.PRODUCT_LABEL: {
        'product', 'ingredients', 'organic', 'produce', 'packed', 'weight',
        'food',
    },
    EvidenceDocument.DocumentType.BUSINESS_DOCUMENT: {
        'business', 'company', 'registration', 'registered', 'organization',
        'organisation', 'farm', 'agriculture',
    },
    EvidenceDocument.DocumentType.OTHER: MARKETPLACE_TERMS,
}

DATE_PATTERNS = (
    re.compile(r'\b(?P<year>20\d{2})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})\b'),
    re.compile(r'\b(?P<day>\d{1,2})[-/.](?P<month>\d{1,2})[-/.](?P<year>20\d{2})\b'),
    re.compile(
        r'\b(?P<day>\d{1,2})\s+'
        r'(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+(?P<year>20\d{2})\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+(?P<day>\d{1,2}),?\s+(?P<year>20\d{2})\b',
        re.IGNORECASE,
    ),
)

EXPIRY_MARKERS = re.compile(
    r'\b(expir(?:y|es|ation)|valid\s+(?:until|through|to)|good\s+through)\b',
    re.IGNORECASE,
)

MONTH_NUMBERS = {
    month.lower(): number
    for number, month in enumerate(
        ('January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December'),
        start=1,
    )
}


class ScreeningError(Exception):
    """Raised when a document cannot be screened safely."""


def _parse_date_match(match):
    values = match.groupdict()
    month = values['month']
    if not month.isdigit():
        month = MONTH_NUMBERS[month.lower()]
    try:
        return date(int(values['year']), int(month), int(values['day']))
    except ValueError:
        return None


def extract_expiry_date(text):
    """Return a date only when it appears beside an explicit expiry marker."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        marker = EXPIRY_MARKERS.search(line)
        if not marker:
            continue
        relevant_text = line[marker.end():]
        for pattern in DATE_PATTERNS:
            match = pattern.search(relevant_text)
            if match:
                parsed = _parse_date_match(match)
                if parsed:
                    return parsed
        if index + 1 < len(lines):
            for pattern in DATE_PATTERNS:
                match = pattern.search(lines[index + 1])
                if match:
                    parsed = _parse_date_match(match)
                    if parsed:
                        return parsed
    return None


def _extract_pdf_text(file_bytes):
    try:
        with pymupdf.open(stream=file_bytes, filetype='pdf') as document:
            if document.page_count > MAX_DOCUMENT_PAGES:
                raise ScreeningError(
                    f'The PDF has {document.page_count} pages; screening is limited to {MAX_DOCUMENT_PAGES}.'
                )
            text = '\n'.join(page.get_text() for page in document)
            if len(text.strip()) >= MIN_TEXT_LENGTH:
                return text.strip(), False

            pages_text = []
            for page in document:
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes('png')))
                pages_text.append(_ocr_image(image))
            return '\n'.join(pages_text).strip(), True
    except pymupdf.FileDataError as error:
        raise ScreeningError('The uploaded PDF could not be opened or is invalid.') from error
    except pytesseract.TesseractNotFoundError as error:
        raise ScreeningError(
            'This scanned PDF needs OCR, but Tesseract is not installed or configured on the server.'
        ) from error
    except pytesseract.TesseractError as error:
        raise ScreeningError(f'OCR could not read this scanned PDF: {error}') from error


def _extract_image_text(file_bytes):
    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image.thumbnail((3500, 3500))
            return _ocr_image(image).strip()
    except UnidentifiedImageError as error:
        raise ScreeningError('The uploaded image could not be opened or is invalid.') from error
    except pytesseract.TesseractNotFoundError as error:
        raise ScreeningError(
            'Image OCR is unavailable because Tesseract is not installed or configured on the server.'
        ) from error
    except pytesseract.TesseractError as error:
        raise ScreeningError(f'OCR could not read this image: {error}') from error
    except OSError as error:
        raise ScreeningError('The uploaded image could not be read.') from error


def _ocr_image(image):
    command = settings.TESSERACT_CMD or shutil.which('tesseract')
    if not command and os.name == 'nt':
        default_path = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if default_path.is_file():
            command = str(default_path)
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    return pytesseract.image_to_string(image)


def _screen_content(evidence, text):
    findings = []
    recommendation = EvidenceDocument.ScreeningRecommendation.REVIEW
    normalized_text = ' '.join(text.lower().split())

    if len(normalized_text) < MIN_TEXT_LENGTH:
        findings.append({
            'severity': 'warning',
            'code': 'insufficient_text',
            'message': 'Too little text was extracted to assess relevance. A reviewer should inspect the original file.',
        })
    else:
        market_matches = sorted(term for term in MARKETPLACE_TERMS if term in normalized_text)
        type_terms = DOCUMENT_TYPE_TERMS.get(evidence.document_type, MARKETPLACE_TERMS)
        type_matches = sorted(term for term in type_terms if term in normalized_text)
        if not market_matches or not type_matches:
            recommendation = EvidenceDocument.ScreeningRecommendation.IRRELEVANT
            findings.append({
                'severity': 'warning',
                'code': 'relevance_not_detected',
                'message': 'Expected organic-agriculture or document-type terms were not found. The document may be unrelated; verify manually.',
                'marketplace_terms_found': market_matches,
                'document_type_terms_found': type_matches,
            })
        else:
            recommendation = EvidenceDocument.ScreeningRecommendation.LIKELY_RELEVANT
            findings.append({
                'severity': 'info',
                'code': 'relevance_terms_found',
                'message': 'Text contains terms associated with this marketplace and the selected document type.',
                'marketplace_terms_found': market_matches,
                'document_type_terms_found': type_matches,
            })

    extracted_expiry = extract_expiry_date(text)
    expiry_mismatch = (
        evidence.expiry_date is not None
        and extracted_expiry is not None
        and evidence.expiry_date != extracted_expiry
    )
    if expiry_mismatch:
        recommendation = EvidenceDocument.ScreeningRecommendation.REVIEW
        findings.append({
            'severity': 'warning',
            'code': 'expiry_date_mismatch',
            'message': (
                f'The submitted expiry date ({evidence.expiry_date}) differs from the date '
                f'extracted from the document ({extracted_expiry}).'
            ),
        })
    elif evidence.expiry_date or extracted_expiry:
        effective_expiry = evidence.expiry_date or extracted_expiry
        if not evidence.expiry_date:
            evidence.expiry_date = effective_expiry
        if effective_expiry < timezone.localdate():
            recommendation = EvidenceDocument.ScreeningRecommendation.EXPIRED
            findings.append({
                'severity': 'high',
                'code': 'expired',
                'message': f'The document appears to have expired on {effective_expiry}. Confirm the date with the original.',
            })
        elif extracted_expiry:
            findings.append({
                'severity': 'info',
                'code': 'expiry_date_found',
                'message': f'An expiry date of {effective_expiry} was found.',
            })
    elif not evidence.expiry_date:
        findings.append({
            'severity': 'warning',
            'code': 'expiry_not_found',
            'message': 'No expiry date was provided or confidently extracted; a reviewer should check the original.',
        })

    findings.append({
        'severity': 'info',
        'code': 'authenticity_limit',
        'message': 'Automated screening cannot verify the issuer, certificate number, stamp, or signature authenticity.',
    })
    return recommendation, findings, extracted_expiry


def _assessment(recommendation, findings):
    if recommendation == EvidenceDocument.ScreeningRecommendation.LIKELY_RELEVANT:
        ai_recommendation = EvidenceDocument.AIRecommendation.APPROVED
        confidence_score = 85
    elif recommendation == EvidenceDocument.ScreeningRecommendation.IRRELEVANT:
        ai_recommendation = EvidenceDocument.AIRecommendation.REJECTED
        confidence_score = 80
    elif recommendation == EvidenceDocument.ScreeningRecommendation.EXPIRED:
        ai_recommendation = EvidenceDocument.AIRecommendation.REJECTED
        confidence_score = 90
    else:
        ai_recommendation = EvidenceDocument.AIRecommendation.REQUIRES_REVIEW
        confidence_score = 50

    finding_codes = {finding.get('code') for finding in findings}
    if 'insufficient_text' in finding_codes:
        confidence_score = 25
    elif 'expiry_date_mismatch' in finding_codes:
        confidence_score = 45
    return ai_recommendation, confidence_score


def _append_mandatory_document_findings(evidence, findings):
    missing_documents = missing_mandatory_documents(evidence.seller)
    findings.extend({
        'severity': 'critical',
        'code': 'missing_mandatory_document',
        'message': f'CRITICAL MISSING MANDATORY DOCUMENT: {document} required.',
    } for document in missing_documents)
    return bool(missing_documents)


def screen_evidence_document(evidence):
    """Extract local document text and persist rule-based screening findings."""
    evidence.extracted_text = ''
    evidence.screening_status = EvidenceDocument.ScreeningStatus.PENDING
    evidence.screening_recommendation = EvidenceDocument.ScreeningRecommendation.REVIEW
    evidence.screening_findings = []
    evidence.confidence_score = None
    evidence.ai_recommendation = EvidenceDocument.AIRecommendation.REQUIRES_REVIEW
    evidence.audit_reasons = []
    evidence.screened_at = None

    try:
        evidence.file.open('rb')
        try:
            file_bytes = evidence.file.read()
        finally:
            evidence.file.close()

        suffix = Path(evidence.file.name).suffix.lower()
        if suffix == '.pdf':
            text, used_ocr = _extract_pdf_text(file_bytes)
        elif suffix in {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}:
            text = _extract_image_text(file_bytes)
            used_ocr = True
        else:
            raise ScreeningError('Unsupported file type. Upload a PDF or supported image.')

        evidence.extracted_text = text
        recommendation, findings, extracted_expiry = _screen_content(evidence, text)
        if extracted_expiry and not evidence.expiry_date:
            evidence.expiry_date = extracted_expiry
        evidence.screening_recommendation = recommendation
        evidence.screening_findings = findings
        evidence.screening_status = EvidenceDocument.ScreeningStatus.COMPLETED
        evidence.screened_at = timezone.now()
        if used_ocr:
            evidence.screening_findings.append({
                'severity': 'info',
                'code': 'ocr_used',
                'message': 'Text was extracted using local OCR and may contain recognition errors.',
            })
        missing_documents = _append_mandatory_document_findings(
            evidence,
            evidence.screening_findings,
        )
        if missing_documents:
            evidence.ai_recommendation = EvidenceDocument.AIRecommendation.REQUIRES_REVIEW
            evidence.confidence_score = 0
        else:
            evidence.ai_recommendation, evidence.confidence_score = _assessment(
                recommendation,
                evidence.screening_findings,
            )
        evidence.audit_reasons = evidence.screening_findings
    except ScreeningError as error:
        logger.warning('Evidence screening failed for document %s: %s', evidence.pk, error)
        evidence.screening_status = EvidenceDocument.ScreeningStatus.FAILED
        evidence.screening_recommendation = EvidenceDocument.ScreeningRecommendation.REVIEW
        evidence.screening_findings = [{
            'severity': 'warning',
            'code': 'screening_failed',
            'message': str(error),
        }, {
            'severity': 'info',
            'code': 'authenticity_limit',
            'message': 'Automated screening cannot verify the issuer, certificate number, stamp, or signature authenticity.',
        }]
        missing_documents = _append_mandatory_document_findings(
            evidence,
            evidence.screening_findings,
        )
        if missing_documents:
            evidence.confidence_score = 0
        evidence.ai_recommendation = EvidenceDocument.AIRecommendation.REQUIRES_REVIEW
        evidence.audit_reasons = evidence.screening_findings
        evidence.screened_at = timezone.now()
    evidence.save(update_fields=[
        'extracted_text',
        'expiry_date',
        'screening_status',
        'screening_recommendation',
        'screening_findings',
        'screened_at',
        'confidence_score',
        'ai_recommendation',
        'audit_reasons',
        'updated_at',
    ])
    return evidence
