from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from verification.models import EvidenceDocument
from .models import SellerProfile


class SellerOnboardingComplianceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='onboardingseller',
            email='onboardingseller@example.com',
            password='SafePassword!8274',
            role=User.Role.SELLER,
        )
        self.seller = SellerProfile.objects.create(
            user=self.user,
            business_name='Onboarding Farm',
            location='Harare',
        )
        self.client.force_login(self.user)

    def test_profile_submission_is_held_until_mandatory_documents_are_uploaded(self):
        response = self.client.post(
            reverse('sellers:onboarding'),
            {
                'business_name': 'Onboarding Farm',
                'seller_type': SellerProfile.SellerType.INDIVIDUAL_FARMER,
                'description': 'Organic vegetables.',
                'location': 'Harare',
                'farm_size_hectares': '',
                'years_operating': 1,
            },
            follow=True,
        )

        self.assertContains(response, 'verification submission is blocked')
        self.seller.refresh_from_db()
        self.assertEqual(
            self.seller.verification_status,
            SellerProfile.VerificationStatus.ADDITIONAL_EVIDENCE_REQUIRED,
        )

    def test_certificate_or_pgs_satisfies_the_organic_document_requirement(self):
        for document_type, title in (
            (EvidenceDocument.DocumentType.PGS_RECORD, 'PGS Record'),
            (EvidenceDocument.DocumentType.BUSINESS_DOCUMENT, 'Registration'),
            (EvidenceDocument.DocumentType.INSPECTION_RECORD, 'Inspection'),
        ):
            EvidenceDocument.objects.create(
                seller=self.seller,
                document_type=document_type,
                title=title,
                file=f'evidence_documents/{document_type.lower()}.pdf',
            )

        response = self.client.post(
            reverse('sellers:onboarding'),
            {
                'business_name': 'Onboarding Farm',
                'seller_type': SellerProfile.SellerType.INDIVIDUAL_FARMER,
                'description': 'Organic vegetables.',
                'location': 'Harare',
                'farm_size_hectares': '',
                'years_operating': 1,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.PENDING)
