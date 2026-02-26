"""
Tests for Doctor CRUD APIs. List/retrieve can be public; create/update/delete require auth.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from doctors.models import Doctor


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
class DoctorAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", name="Test User", password="pass12345"
        )
        self.list_url = reverse("doctor-list")

    def authenticate(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "pass12345"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_doctor_requires_auth(self):
        payload = {
            "name": "Jane Smith",
            "specialization": "Cardiology",
            "email": "jane@hospital.com",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_doctor_success(self):
        self.authenticate()
        payload = {
            "name": "Jane Smith",
            "specialization": "Cardiology",
            "email": "jane@hospital.com",
            "experience_years": 5,
            "phone_number": "1234567890"
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "jane@hospital.com")
        self.assertEqual(response.data["first_name"], "Jane")
        self.assertEqual(response.data["last_name"], "Smith")
        self.assertEqual(response.data["experience_years"], 5)
        self.assertTrue(Doctor.objects.filter(email="jane@hospital.com").exists())

    def test_create_doctor_without_email_and_phone_success(self):
        self.authenticate()
        payload = {
            "name": "Dr SingleName",
            "specialization": "General",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "Dr")
        self.assertEqual(response.data["last_name"], "SingleName")
        self.assertIsNone(response.data.get("email"))

    def test_list_doctors_public(self):
        Doctor.objects.create(
            first_name="A", last_name="Doc", specialization="General", email="a@doc.com"
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_retrieve_doctor_public(self):
        doctor = Doctor.objects.create(
            first_name="B", last_name="Doc", specialization="Surgery", email="b@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "B")

    def test_update_doctor_requires_auth(self):
        doctor = Doctor.objects.create(
            first_name="C", last_name="Doc", specialization="GP", email="c@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.put(
            url,
            {
                "name": "C Doc",
                "specialization": "GP",
                "email": "c@doc.com",
                "phone_number": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_doctor_put_treats_as_partial_success(self):
        self.authenticate()
        doctor = Doctor.objects.create(
            first_name="C", last_name="Doc", specialization="GP", email="c@doc.com", experience_years=2
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.put(
            url,
            {"name": "NewDoctor Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertEqual(doctor.first_name, "NewDoctor")
        self.assertEqual(doctor.last_name, "Name")
        self.assertEqual(doctor.experience_years, 2)

    def test_update_doctor_patch_success(self):
        self.authenticate()
        doctor = Doctor.objects.create(
            first_name="Old", last_name="Man", specialization="GP", email="old@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.patch(url, {"specialization": "Cardiology"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertEqual(doctor.specialization, "Cardiology")

    def test_delete_doctor_requires_auth(self):
        doctor = Doctor.objects.create(
            first_name="D", last_name="Doc", specialization="GP", email="d@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_doctor_success(self):
        self.authenticate()
        doctor = Doctor.objects.create(
            first_name="E", last_name="Doc", specialization="GP", email="e@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Doctor.objects.filter(pk=doctor.pk).exists())

    def test_duplicate_doctor_email_fails_on_create(self):
        self.authenticate()
        Doctor.objects.create(
            first_name="F", last_name="Doc", specialization="GP", email="f@doc.com"
        )
        response = self.client.post(
            self.list_url,
            {
                "name": "F2 Doc",
                "specialization": "GP",
                "email": "F@DOC.COM", # Testing case insensitivity
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_duplicate_doctor_email_fails_on_update(self):
        self.authenticate()
        Doctor.objects.create(
            first_name="G", last_name="Doc", specialization="GP", email="g@doc.com"
        )
        doctor2 = Doctor.objects.create(
            first_name="H", last_name="Doc", specialization="GP", email="h@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor2.pk})
        response = self.client.patch(
            url,
            {"email": "g@doc.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_update_same_email_success(self):
        self.authenticate()
        doctor = Doctor.objects.create(
            first_name="I", last_name="Doc", specialization="GP", email="i@doc.com"
        )
        url = reverse("doctor-detail", kwargs={"pk": doctor.pk})
        response = self.client.patch(
            url,
            {"email": "i@doc.com", "specialization": "Surgery"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertEqual(doctor.specialization, "Surgery")
