from django import forms
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import authenticate
from auth_app.models import User


class RegistrationViewTests(TestCase):
    def test_registration_logs_in_new_user(self):
        response = self.client.post(
            reverse('auth_app:register'),
            {
                'username': 'newbuyer',
                'email': 'newbuyer@example.com',
                'phone_number': '',
                'role': 'BUYER',
                'password1': 'SafePassword!8274',
                'password2': 'SafePassword!8274',
            },
        )

        self.assertRedirects(response, reverse('dashboard:home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class EmailAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='emailuser',
            email='emailuser@example.com',
            password='SafePassword!8274',
        )

    def test_authenticates_with_email(self):
        user = authenticate(username='emailuser@example.com', password='SafePassword!8274')

        self.assertEqual(user, self.user)

    def test_does_not_authenticate_with_username(self):
        user = authenticate(username='emailuser', password='SafePassword!8274')

        self.assertIsNone(user)

    def test_login_view_accepts_email(self):
        response = self.client.post(
            reverse('auth_app:login'),
            {'username': 'emailuser@example.com', 'password': 'SafePassword!8274'},
        )

        self.assertRedirects(response, reverse('dashboard:home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_view_rejects_username(self):
        response = self.client.post(
            reverse('auth_app:login'),
            {'username': 'emailuser', 'password': 'SafePassword!8274'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class AdminEmailAuthenticationTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='SafePassword!8274',
        )

    def test_admin_login_form_uses_email_field(self):
        response = self.client.get(reverse('admin:login'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].fields['username'].label, 'Email')
        self.assertIsInstance(response.context['form'].fields['username'], forms.EmailField)

    def test_admin_login_accepts_email(self):
        response = self.client.post(
            reverse('admin:login'),
            {
                'username': 'admin@example.com',
                'password': 'SafePassword!8274',
                'next': reverse('admin:index'),
            },
        )

        self.assertRedirects(response, reverse('admin:index'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.admin_user.pk)
