import io
import tempfile
from datetime import date
from unittest.mock import patch

import pymupdf
from PIL import Image
import pytesseract
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from auth_app.models import User
from sellers.models import SellerProfile
from verification.models import EvidenceDocument
from .services import extract_expiry_date, screen_evidence_document


def make_pdf(text):
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    contents = document.tobytes()
    document.close()
    return contents


class EvidenceScreeningServiceTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()

        user = User.objects.create_user(
            username='screeningseller',
            email='screeningseller@example.com',
            password='SafePassword!8274',
            role=User.Role.SELLER,
        )
        seller = SellerProfile.objects.create(
            user=user,
            business_name='Test Organic Farm',
            location='Harare',
        )
        self.evidence = EvidenceDocument.objects.create(
            seller=seller,
            document_type=EvidenceDocument.DocumentType.CERTIFICATE,
            title='Organic certificate',
            file=SimpleUploadedFile(
                'certificate.pdf',
                make_pdf(
                    'Organic farming certificate issued to a PGS farm. '
                    'Expiry date: 01/01/2020. Certificate number 12345.'
                ),
                content_type='application/pdf',
            ),
        )
        EvidenceDocument.objects.create(
            seller=seller,
            document_type=EvidenceDocument.DocumentType.BUSINESS_DOCUMENT,
            title='Business registration',
            file='evidence_documents/business-registration.pdf',
            status=EvidenceDocument.Status.ACCEPTED,
        )
        EvidenceDocument.objects.create(
            seller=seller,
            document_type=EvidenceDocument.DocumentType.INSPECTION_RECORD,
            title='Farm inspection',
            file='evidence_documents/farm-inspection.pdf',
            status=EvidenceDocument.Status.ACCEPTED,
        )

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def test_extracts_text_and_flags_expired_relevant_certificate(self):
        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.screening_status, EvidenceDocument.ScreeningStatus.COMPLETED)
        self.assertEqual(self.evidence.screening_recommendation, EvidenceDocument.ScreeningRecommendation.EXPIRED)
        self.assertEqual(self.evidence.expiry_date, date(2020, 1, 1))
        self.assertIn('organic', self.evidence.extracted_text.lower())
        self.assertTrue(any(finding['code'] == 'expired' for finding in self.evidence.screening_findings))
        self.assertTrue(any(finding['code'] == 'authenticity_limit' for finding in self.evidence.screening_findings))
        self.assertEqual(self.evidence.confidence_score, 90)
        self.assertEqual(self.evidence.ai_recommendation, EvidenceDocument.AIRecommendation.REJECTED)
        self.assertEqual(self.evidence.audit_reasons, self.evidence.screening_findings)
        self.assertEqual(self.evidence.status, EvidenceDocument.Status.UPLOADED)

    def test_expiry_mismatch_requires_manual_review(self):
        self.evidence.expiry_date = date(2030, 1, 1)
        self.evidence.save(update_fields=['expiry_date'])

        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(
            self.evidence.screening_recommendation,
            EvidenceDocument.ScreeningRecommendation.REVIEW,
        )
        self.assertTrue(any(
            finding['code'] == 'expiry_date_mismatch'
            for finding in self.evidence.screening_findings
        ))

    def test_missing_mandatory_documents_force_zero_confidence_and_manual_review(self):
        EvidenceDocument.objects.filter(
            seller=self.evidence.seller,
            document_type=EvidenceDocument.DocumentType.BUSINESS_DOCUMENT,
        ).delete()
        EvidenceDocument.objects.filter(
            seller=self.evidence.seller,
            document_type=EvidenceDocument.DocumentType.INSPECTION_RECORD,
        ).delete()

        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.confidence_score, 0)
        self.assertEqual(
            self.evidence.ai_recommendation,
            EvidenceDocument.AIRecommendation.REQUIRES_REVIEW,
        )
        missing_findings = [
            finding for finding in self.evidence.audit_reasons
            if finding['code'] == 'missing_mandatory_document'
        ]
        self.assertEqual(len(missing_findings), 2)
        self.assertTrue(all(finding['severity'] == 'critical' for finding in missing_findings))
        self.assertIn('Business Registration Document required.', missing_findings[0]['message'])
        self.assertIn('Farm Inspection Record required.', missing_findings[1]['message'])

    def test_flags_unrelated_document_without_claiming_it_is_fake(self):
        self.evidence.file.save(
            'unrelated.pdf',
            SimpleUploadedFile(
                'unrelated.pdf',
                make_pdf('University mathematics examination results for student number 123456.'),
                content_type='application/pdf',
            ),
            save=True,
        )
        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(
            self.evidence.screening_recommendation,
            EvidenceDocument.ScreeningRecommendation.IRRELEVANT,
        )
        self.assertTrue(any(
            finding['code'] == 'relevance_not_detected'
            for finding in self.evidence.screening_findings
        ))

    @patch('ai_engine.services.pytesseract.image_to_string')
    def test_ocr_text_is_screened_for_images(self, image_to_string):
        image_to_string.return_value = 'Organic certificate for PGS farming. Expiry date: 01/01/2030.'
        output = io.BytesIO()
        Image.new('RGB', (40, 40), 'white').save(output, format='PNG')
        self.evidence.file.save(
            'certificate.png',
            SimpleUploadedFile('certificate.png', output.getvalue(), content_type='image/png'),
            save=True,
        )

        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.screening_status, EvidenceDocument.ScreeningStatus.COMPLETED)
        self.assertIn('organic certificate', self.evidence.extracted_text.lower())
        self.assertTrue(any(finding['code'] == 'ocr_used' for finding in self.evidence.screening_findings))

    @patch(
        'ai_engine.services.pytesseract.image_to_string',
        side_effect=pytesseract.TesseractNotFoundError(),
    )
    def test_missing_ocr_engine_is_reported_for_manual_review(self, image_to_string):
        output = io.BytesIO()
        Image.new('RGB', (40, 40), 'white').save(output, format='PNG')
        self.evidence.file.save(
            'scanned-certificate.png',
            SimpleUploadedFile('scanned-certificate.png', output.getvalue(), content_type='image/png'),
            save=True,
        )

        screen_evidence_document(self.evidence)

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.screening_status, EvidenceDocument.ScreeningStatus.FAILED)
        self.assertEqual(
            self.evidence.screening_recommendation,
            EvidenceDocument.ScreeningRecommendation.REVIEW,
        )
        self.assertIn('Tesseract', self.evidence.screening_findings[0]['message'])

    def test_expiry_parser_requires_explicit_expiry_label(self):
        self.assertEqual(
            extract_expiry_date('Issue date: 01/01/2020\nExpiry date: 31/12/2030'),
            date(2030, 12, 31),
        )
        self.assertIsNone(extract_expiry_date('Issue date: 01/01/2020'))
