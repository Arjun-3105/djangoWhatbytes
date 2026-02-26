"""
Tests for authentication APIs: register and login with JWT.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
class AuthAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("auth-register")
        self.login_url = reverse("auth-login")

    def test_register_success(self):
        payload = {
            "email": "user@example.com",
            "name": "Test User",
            "password": "securepass123",
            "password_confirm": "securepass123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["name"], "Test User")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.filter(email="user@example.com").exists())

    def test_register_without_password_confirm_success(self):
        payload = {
            "email": "user2@example.com",
            "name": "Test User 2",
            "password": "securepass123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "user2@example.com")

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(email="existing@example.com", name="Existing", password="pass123456")
        payload = {
            "email": "existing@example.com",
            "name": "New User",
            "password": "securepass123",
            "password_confirm": "securepass123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_password_mismatch_fails(self):
        payload = {
            "email": "user@example.com",
            "name": "Test User",
            "password": "securepass123",
            "password_confirm": "different",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_register_short_password_fails(self):
        payload = {
            "email": "user@example.com",
            "name": "Test User",
            "password": "short",
            "password_confirm": "short",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_invalid_email_fails(self):
        payload = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "securepass123",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_required_fields_fails(self):
        response = self.client.post(self.register_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_login_success(self):
        User.objects.create_user(email="login@example.com", name="Login User", password="mypass123")
        payload = {"email": "login@example.com", "password": "mypass123"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_login_wrong_password_fails(self):
        User.objects.create_user(email="login@example.com", name="Login User", password="mypass123")
        response = self.client.post(
            self.login_url,
            {"email": "login@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user_fails(self):
        response = self.client.post(
            self.login_url,
            {"email": "nobody@example.com", "password": "anypass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user_fails(self):
        user = User.objects.create_user(email="inactive@example.com", name="Inactive User", password="mypass123")
        user.is_active = False
        user.save()
        response = self.client.post(
            self.login_url,
            {"email": "inactive@example.com", "password": "mypass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
