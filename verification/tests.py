import tempfile

import pymupdf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from auth_app.models import User
from sellers.models import SellerProfile
from .models import EvidenceDocument


def make_pdf(text):
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    contents = document.tobytes()
    document.close()
    return contents


class EvidenceDocumentViewTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()

        self.user = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='SafePassword!8274',
            role=User.Role.SELLER,
        )
        self.seller = SellerProfile.objects.create(
            user=self.user,
            business_name='Test Farm',
            location='Harare',
        )
        self.client.force_login(self.user)

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def _upload(self, document_type='CERTIFICATE', filename='certificate.pdf'):
        return self.client.post(
            reverse('verification:upload_evidence'),
            {
                'document_type': document_type,
                'title': 'Organic certificate',
                'file': SimpleUploadedFile(
                    filename,
                    make_pdf('Organic certificate for a Zimbabwean farm. PGS certified.'),
                    content_type='application/pdf',
                ),
                'issue_date': '',
                'expiry_date': '',
            },
        )

    def test_seller_cannot_upload_same_document_type_twice(self):
        self._upload()

        response = self._upload(filename='duplicate.pdf')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EvidenceDocument.objects.filter(seller=self.seller, document_type='CERTIFICATE').count(),
            1,
        )
        self.assertContains(response, 'Update the existing document instead.')

    def test_seller_can_replace_existing_document(self):
        self._upload()
        evidence = EvidenceDocument.objects.get(seller=self.seller, document_type='CERTIFICATE')
        evidence.status = EvidenceDocument.Status.ACCEPTED
        evidence.review_notes = 'Needs another page'
        evidence.extracted_text = 'Old extracted text'
        evidence.save()

        response = self.client.post(
            reverse('verification:update_evidence', args=[evidence.pk]),
            {
                'document_type': 'CERTIFICATE',
                'title': 'Updated organic certificate',
                'file': SimpleUploadedFile(
                    'replacement.pdf',
                    make_pdf('Updated organic certificate for a Zimbabwean farm. PGS certified.'),
                    content_type='application/pdf',
                ),
                'issue_date': '',
                'expiry_date': '',
            },
        )

        evidence.refresh_from_db()
        self.assertRedirects(response, reverse('verification:evidence_list'))
        self.assertEqual(EvidenceDocument.objects.filter(seller=self.seller).count(), 1)
        self.assertEqual(evidence.title, 'Updated organic certificate')
        self.assertEqual(evidence.file.name.rsplit('/', 1)[-1], 'replacement.pdf')
        self.assertEqual(evidence.status, EvidenceDocument.Status.REQUIRES_REVIEW)
        self.assertEqual(evidence.review_notes, '')
        self.assertIn('updated organic certificate', evidence.extracted_text.lower())
        self.assertEqual(evidence.screening_status, EvidenceDocument.ScreeningStatus.COMPLETED)


class EvidenceDocumentAdminTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()

        self.admin = User.objects.create_superuser(
            username='reviewadmin',
            email='reviewadmin@example.com',
            password='SafePassword!8274',
        )
        self.seller_user = User.objects.create_user(
            username='reviewedseller',
            email='farmer@example.com',
            password='SafePassword!8274',
            phone_number='+263771234567',
            role=User.Role.SELLER,
        )
        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            business_name='Ruwa Organic Farms',
            seller_type=SellerProfile.SellerType.COMMERCIAL_FARM,
            location='Ruwa, Mashonaland East',
            description='Chemical-free organic produce under PGS guidelines.',
            farm_size_hectares='12.50',
            years_operating=8,
        )
        self.evidence = EvidenceDocument.objects.create(
            seller=self.seller,
            document_type=EvidenceDocument.DocumentType.CERTIFICATE,
            title='Annual organic certificate',
            file=SimpleUploadedFile(
                'certificate.pdf',
                b'certificate contents',
                content_type='application/pdf',
            ),
            status=EvidenceDocument.Status.REQUIRES_REVIEW,
            extracted_text='Organic PGS certificate; review needed.',
        )
        self.client.force_login(self.admin)

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def test_seller_admin_page_shows_submitted_details_and_evidence(self):
        response = self.client.get(
            reverse('admin:sellers_sellerprofile_change', args=[self.seller.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ruwa Organic Farms')
        self.assertContains(response, 'farmer@example.com')
        self.assertContains(response, '+263771234567')
        self.assertContains(response, 'Chemical-free organic produce')
        self.assertContains(response, 'Annual organic certificate')
        self.assertContains(response, 'Organic PGS certificate; review needed.')

    def test_admin_can_open_evidence_document_and_uploaded_file(self):
        response = self.client.get(
            reverse(
                'admin:verification_evidencedocument_change',
                args=[self.evidence.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ruwa Organic Farms')
        self.assertContains(response, 'View document')
        self.assertContains(response, 'Organic PGS certificate; review needed.')
