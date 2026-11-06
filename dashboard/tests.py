from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from sellers.models import SellerProfile
from verification.models import EvidenceDocument


class DashboardRoleRoutingTests(TestCase):
    def test_anonymous_user_is_redirected_to_project_login(self):
        response = self.client.get(reverse('dashboard:home'))

        self.assertRedirects(
            response,
            f"{reverse('auth_app:login')}?next={reverse('dashboard:home')}",
        )

    def test_staff_user_with_buyer_role_sees_admin_dashboard(self):
        admin_user = User.objects.create_user(
            username='adminbuyer',
            email='adminbuyer@example.com',
            password='SafePassword!8274',
            role=User.Role.BUYER,
            is_staff=True,
        )
        self.assertEqual(admin_user.role, User.Role.BUYER)
        self.client.force_login(admin_user)

        response = self.client.get(reverse('dashboard:home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin_home.html')
        self.assertContains(response, 'Manage sellers')
        self.assertContains(response, 'Manage customers')
        self.assertNotContains(response, '/admin/sellers/')
        self.assertContains(response, reverse('dashboard:sellers'))
        self.assertContains(response, reverse('dashboard:customers'))

    def test_buyer_sees_marketplace_home(self):
        buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='SafePassword!8274',
            role=User.Role.BUYER,
        )
        self.client.force_login(buyer)

        response = self.client.get(reverse('dashboard:home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/home.html')

    def test_admin_dashboard_links_to_evidence_review_queue(self):
        admin_user = User.objects.create_superuser(
            username='reviewadmin',
            email='reviewadmin@example.com',
            password='SafePassword!8274',
        )
        seller_user = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='SafePassword!8274',
            role=User.Role.SELLER,
        )
        seller = SellerProfile.objects.create(
            user=seller_user,
            business_name='Test Farm',
            location='Harare',
        )
        EvidenceDocument.objects.create(
            seller=seller,
            document_type=EvidenceDocument.DocumentType.CERTIFICATE,
            title='Certificate',
            file='evidence_documents/certificate.pdf',
            status=EvidenceDocument.Status.REQUIRES_REVIEW,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('dashboard:home'))

        self.assertEqual(response.context['evidence_review_count'], 1)
        self.assertContains(response, 'Review documents')


class WebsiteAdminManagementTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='siteadmin',
            email='siteadmin@example.com',
            password='SafePassword!8274',
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='SafePassword!8274',
            role=User.Role.BUYER,
        )
        self.seller_user = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='SafePassword!8274',
            role=User.Role.SELLER,
        )
        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            business_name='Ruwa Organic Farms',
            location='Ruwa',
        )
        self.evidence = EvidenceDocument.objects.create(
            seller=self.seller,
            document_type=EvidenceDocument.DocumentType.CERTIFICATE,
            title='Organic certificate',
            file='evidence_documents/certificate.pdf',
            status=EvidenceDocument.Status.REQUIRES_REVIEW,
            extracted_text='Certificate text for manual review.',
        )
        self.client.force_login(self.admin_user)

    def _approve_required_documents(self):
        self.evidence.status = EvidenceDocument.Status.ACCEPTED
        self.evidence.save(update_fields=['status', 'updated_at'])
        for document_type, title in (
            (EvidenceDocument.DocumentType.BUSINESS_DOCUMENT, 'Business registration'),
            (EvidenceDocument.DocumentType.INSPECTION_RECORD, 'Farm inspection'),
        ):
            EvidenceDocument.objects.create(
                seller=self.seller,
                document_type=document_type,
                title=title,
                file=f'evidence_documents/{document_type.lower()}.pdf',
                status=EvidenceDocument.Status.ACCEPTED,
            )

    def test_admin_can_manage_sellers_customers_and_evidence_in_site(self):
        response = self.client.get(reverse('dashboard:sellers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ruwa Organic Farms')

        response = self.client.get(reverse('dashboard:seller_detail', args=[self.seller.pk]))
        self.assertContains(response, 'Certificate text for manual review.')
        self.assertContains(response, reverse('dashboard:evidence_detail', args=[self.evidence.pk]))

        response = self.client.get(reverse('dashboard:customers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'customer@example.com')

        response = self.client.get(reverse('dashboard:customer_detail', args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'customer@example.com')

        response = self.client.get(reverse('dashboard:evidence'))
        self.assertContains(response, 'Organic certificate')

    def test_admin_can_update_seller_and_document_review_status(self):
        self._approve_required_documents()
        response = self.client.post(
            reverse('dashboard:seller_detail', args=[self.seller.pk]),
            {'verification_status': SellerProfile.VerificationStatus.VERIFIED},
        )
        self.assertRedirects(
            response,
            reverse('dashboard:seller_detail', args=[self.seller.pk]),
        )
        self.seller.refresh_from_db()
        self.assertEqual(
            self.seller.verification_status,
            SellerProfile.VerificationStatus.VERIFIED,
        )

        response = self.client.post(
            reverse('dashboard:evidence_detail', args=[self.evidence.pk]),
            {
                'status': EvidenceDocument.Status.REJECTED,
                'review_notes': 'Please submit a clearer scan.',
            },
        )
        self.assertRedirects(
            response,
            reverse('dashboard:evidence_detail', args=[self.evidence.pk]),
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.status, EvidenceDocument.Status.REJECTED)
        self.assertEqual(self.evidence.review_notes, 'Please submit a clearer scan.')
        self.assertEqual(self.evidence.reviewed_by, self.admin_user)

    def test_seller_cannot_be_verified_until_all_mandatory_evidence_is_approved(self):
        response = self.client.post(
            reverse('dashboard:seller_detail', args=[self.seller.pk]),
            {'verification_status': SellerProfile.VerificationStatus.VERIFIED},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seller cannot be verified until all mandatory documents are approved')
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.PENDING)

    def test_staff_can_reject_and_approve_seller_with_audit_reason(self):
        response = self.client.post(
            reverse('dashboard:verify_seller', args=[self.seller.pk]),
            {'action': 'reject'},
        )
        self.assertRedirects(
            response,
            reverse('dashboard:seller_detail', args=[self.seller.pk]),
        )
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.PENDING)

        self.client.post(
            reverse('dashboard:verify_seller', args=[self.seller.pk]),
            {'action': 'reject', 'rejection_reason': 'The certificate has expired.'},
        )
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.REJECTED)
        self.assertEqual(self.seller.rejection_reason, 'The certificate has expired.')

        self.client.post(
            reverse('dashboard:verify_seller', args=[self.seller.pk]),
            {'action': 'approve'},
        )
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.REJECTED)
        self.assertEqual(self.seller.rejection_reason, 'The certificate has expired.')

        self._approve_required_documents()
        self.client.post(
            reverse('dashboard:verify_seller', args=[self.seller.pk]),
            {'action': 'approve'},
        )
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.verification_status, SellerProfile.VerificationStatus.VERIFIED)
        self.assertEqual(self.seller.rejection_reason, '')

    def test_staff_can_approve_and_reject_evidence_with_review_audit(self):
        self.client.post(
            reverse('dashboard:verify_evidence', args=[self.evidence.pk]),
            {'action': 'approve'},
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.status, EvidenceDocument.Status.ACCEPTED)
        self.assertEqual(self.evidence.reviewed_by, self.admin_user)

        self.client.post(
            reverse('dashboard:verify_evidence', args=[self.evidence.pk]),
            {'action': 'reject', 'review_notes': 'The document is not a farm certificate.'},
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.status, EvidenceDocument.Status.REJECTED)
        self.assertEqual(self.evidence.review_notes, 'The document is not a farm certificate.')

    def test_compliance_dashboard_separates_seller_states_and_links_ai_report(self):
        self._approve_required_documents()
        self.seller.verification_status = SellerProfile.VerificationStatus.VERIFIED
        self.seller.save()
        self.evidence.status = EvidenceDocument.Status.ACCEPTED
        self.evidence.confidence_score = 85
        self.evidence.ai_recommendation = EvidenceDocument.AIRecommendation.APPROVED
        self.evidence.audit_reasons = [{'severity': 'info', 'message': 'Organic terms found.'}]
        self.evidence.save()

        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(reverse('dashboard:seller_detail', args=[self.seller.pk]))
        self.assertContains(detail, 'Mandatory compliance checklist')
        self.assertContains(detail, 'Business Registration Document')
        self.assertContains(detail, 'Farm Inspection Record')
        self.assertContains(detail, 'Approved')
        self.assertEqual(response.context['active_seller_count'], 1)
        self.assertEqual(response.context['verified_evidence_count'], 3)
        self.assertContains(response, reverse('ai_engine:analysis_report', args=[self.evidence.pk]))
        self.assertContains(response, 'Verified sellers')
        self.assertContains(response, 'Sellers pending verification')
        self.assertContains(response, 'Rejected sellers')

        report = self.client.get(reverse('ai_engine:analysis_report', args=[self.evidence.pk]))
        self.assertEqual(report.status_code, 200)
        self.assertContains(report, 'Organic terms found.')

    def test_non_admin_cannot_access_site_management(self):
        buyer = User.objects.create_user(
            username='buyer2',
            email='buyer2@example.com',
            password='SafePassword!8274',
            role=User.Role.BUYER,
        )
        self.client.force_login(buyer)

        response = self.client.get(reverse('dashboard:sellers'))

        self.assertEqual(response.status_code, 403)

    def test_admin_role_without_staff_flag_cannot_access_compliance_dashboard(self):
        non_staff_admin = User.objects.create_user(
            username='unstaffedadmin',
            email='unstaffedadmin@example.com',
            password='SafePassword!8274',
            role=User.Role.ADMIN,
            is_staff=False,
        )
        self.client.force_login(non_staff_admin)

        self.assertEqual(self.client.get(reverse('dashboard:home')).status_code, 403)
        self.assertEqual(self.client.get(reverse('ai_engine:analysis_report', args=[self.evidence.pk])).status_code, 403)
