"""
Tests for Patient CRUD APIs. Patients are scoped to the authenticated user.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from patients.models import Patient


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
class PatientAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="staff@example.com", name="Staff User", password="pass12345"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", name="Other User", password="pass12345"
        )
        self.patient_list_url = reverse("patient-list")
        self.authenticate(self.user)

    def authenticate(self, user):
        response = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "pass12345"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_patient_success(self):
        payload = {
            "name": "John Doe",
            "age": 30,
            "gender": "male",
            "address": "123 Main St",
        }
        response = self.client.post(self.patient_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "John")
        self.assertEqual(response.data["last_name"], "Doe")
        self.assertEqual(response.data["age"], 30)
        patient = Patient.objects.get(first_name="John")
        self.assertEqual(patient.created_by, self.user)
        self.assertEqual(patient.medical_history, "")

    def test_create_patient_with_medical_history_success(self):
        payload = {
            "name": "SingleName",
            "age": 45,
            "gender": "female",
            "medical_history": "Diabetes",
        }
        response = self.client.post(self.patient_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "SingleName")
        self.assertEqual(response.data["last_name"], "")
        self.assertEqual(response.data["gender"], "female")
        patient = Patient.objects.get(first_name="SingleName")
        self.assertEqual(patient.medical_history, "Diabetes")

    def test_list_patients_only_own(self):
        Patient.objects.create(
            created_by=self.user, first_name="A", last_name="", age=25, gender="female"
        )
        Patient.objects.create(
            created_by=self.other_user, first_name="B", last_name="", age=40, gender="male"
        )
        response = self.client.get(self.patient_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["first_name"], "A")

    def test_retrieve_patient_success(self):
        patient = Patient.objects.create(
            created_by=self.user, first_name="Jane", last_name="Doe", age=28, gender="female"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Jane")

    def test_retrieve_other_user_patient_forbidden(self):
        patient = Patient.objects.create(
            created_by=self.other_user, first_name="Other", last_name="", age=50, gender="male"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_patient_put_treats_as_partial_success(self):
        patient = Patient.objects.create(
            created_by=self.user, first_name="Old", last_name="Name", age=22, gender="male", address="Old Address"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        # Try updating only name, ensure other fields like address remain intact
        response = self.client.put(
            url,
            {"name": "New Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEqual(patient.first_name, "New")
        self.assertEqual(patient.last_name, "Name")
        self.assertEqual(patient.address, "Old Address")

    def test_update_patient_patch_success(self):
        patient = Patient.objects.create(
            created_by=self.user, first_name="Old", last_name="Name", age=22, gender="male"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.patch(
            url,
            {"age": 25, "gender": "other"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEqual(patient.age, 25)
        self.assertEqual(patient.gender, "other")

    def test_update_other_user_patient_forbidden(self):
        patient = Patient.objects.create(
            created_by=self.other_user, first_name="Other", last_name="", age=50, gender="male"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.patch(url, {"age": 55}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_patient_success(self):
        patient = Patient.objects.create(
            created_by=self.user, first_name="ToDelete", last_name="", age=20, gender="other"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(pk=patient.pk).exists())

    def test_delete_other_user_patient_forbidden(self):
        patient = Patient.objects.create(
            created_by=self.other_user, first_name="Other", last_name="", age=50, gender="male"
        )
        url = reverse("patient-detail", kwargs={"pk": patient.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_requests_forbidden(self):
        self.client.credentials()
        url = reverse("patient-list")
        response = self.client.post(url, {"name": "X", "age": 1, "gender": "male"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_validation_age_negative_or_zero_invalid(self):
        response = self.client.post(
            self.patient_list_url,
            {"name": "X", "age": 0, "gender": "male"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("age", response.data)

        response2 = self.client.post(
            self.patient_list_url,
            {"name": "X", "age": -5, "gender": "male"},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validation_age_too_high_invalid(self):
        response = self.client.post(
            self.patient_list_url,
            {"name": "X", "age": 131, "gender": "male"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("age", response.data)

    def test_validation_gender_invalid(self):
        response = self.client.post(
            self.patient_list_url,
            {"name": "X", "age": 20, "gender": "unknown"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gender", response.data)
