from django.test import TestCase
from django.urls import reverse

from auth_app.models import User


class ProductCatalogAccessTests(TestCase):
    def test_guest_is_redirected_to_login_before_accessing_marketplace(self):
        catalog_url = reverse('products:catalog')

        response = self.client.get(catalog_url)

        self.assertRedirects(
            response,
            f'{reverse("auth_app:login")}?next={catalog_url}',
        )

    def test_marketplace_navigation_is_hidden_for_guest(self):
        response = self.client.get(reverse('auth_app:login'))

        self.assertNotContains(response, reverse('products:catalog'))

    def test_signed_in_buyer_can_access_marketplace(self):
        buyer = User.objects.create_user(
            username='catalogbuyer',
            email='catalogbuyer@example.com',
            password='SafePassword!8274',
            role=User.Role.BUYER,
        )
        self.client.force_login(buyer)

        response = self.client.get(reverse('products:catalog'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/catalog.html')
