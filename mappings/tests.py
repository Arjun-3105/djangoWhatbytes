"""
Tests for Patient-Doctor mapping APIs.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from patients.models import Patient
from doctors.models import Doctor
from mappings.models import PatientDoctorMapping


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
class MappingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", name="Test User", password="pass12345"
        )
        self.patient = Patient.objects.create(
            created_by=self.user, first_name="P", last_name="", age=30, gender="male"
        )
        self.doctor = Doctor.objects.create(
            first_name="D", last_name="Doc", specialization="GP", email="d@doc.com"
        )
        self.list_url = reverse("mapping-list-create")

    def authenticate(self, user=None):
        if user is None:
            user = self.user
        response = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "pass12345"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_mapping_success(self):
        self.authenticate()
        payload = {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PatientDoctorMapping.objects.filter(patient=self.patient, doctor=self.doctor).exists()
        )
        self.assertEqual(response.data["patient_id"], self.patient.pk)
        self.assertEqual(response.data["doctor_id"], self.doctor.pk)
        self.assertIn("patient", response.data)
        self.assertIn("doctor", response.data)

    def test_create_mapping_duplicate_fails(self):
        self.authenticate()
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        payload = {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_create_mapping_for_other_users_patient_fails(self):
        other_user = User.objects.create_user(
            email="other@example.com", name="Other", password="pass12345"
        )
        self.authenticate(other_user) # Logged in as other user
        # Try to assign doctor to the main user's patient
        payload = {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mapping_invalid_doctor_or_patient_fails(self):
        self.authenticate()
        payload = {"patient_id": 9999, "doctor_id": self.doctor.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient_id", response.data)

        payload2 = {"patient_id": self.patient.pk, "doctor_id": 9999}
        response2 = self.client.post(self.list_url, payload2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor_id", response2.data)

    def test_list_mappings_only_own_patients(self):
        self.authenticate()
        other_user = User.objects.create_user(
            email="other3@example.com", name="Other", password="pass12345"
        )
        other_patient = Patient.objects.create(
            created_by=other_user, first_name="O", last_name="", age=25, gender="female"
        )
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        PatientDoctorMapping.objects.create(patient=other_patient, doctor=self.doctor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return the mapping for self.patient
        self.assertEqual(len(response.data["results"] if "results" in response.data else response.data), 1)

    def test_get_doctors_for_patient_success(self):
        self.authenticate()
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        url = reverse("mapping-detail-or-patient", kwargs={"pk": self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["doctor"], str(self.doctor))

    def test_get_doctors_for_other_user_patient_404(self):
        self.authenticate()
        other_user = User.objects.create_user(
            email="other4@example.com", name="Other", password="pass12345"
        )
        other_patient = Patient.objects.create(
            created_by=other_user, first_name="O", last_name="", age=25, gender="female"
        )
        url = reverse("mapping-detail-or-patient", kwargs={"pk": other_patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_doctors_for_nonexistent_patient_404(self):
        self.authenticate()
        url = reverse("mapping-detail-or-patient", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_mapping_success(self):
        self.authenticate()
        mapping = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        url = reverse("mapping-detail-or-patient", kwargs={"pk": mapping.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=mapping.pk).exists())

    def test_delete_other_user_mapping_404(self):
        other_user = User.objects.create_user(
            email="other5@example.com", name="Other", password="pass12345"
        )
        other_patient = Patient.objects.create(
            created_by=other_user, first_name="O", last_name="", age=25, gender="female"
        )
        mapping = PatientDoctorMapping.objects.create(patient=other_patient, doctor=self.doctor)
        
        self.authenticate() # logged in as main user
        url = reverse("mapping-detail-or-patient", kwargs={"pk": mapping.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PatientDoctorMapping.objects.filter(pk=mapping.pk).exists())

    def test_delete_nonexistent_mapping_404(self):
        self.authenticate()
        url = reverse("mapping-detail-or-patient", kwargs={"pk": 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_requests_forbidden(self):
        payload = {"patient_id": self.patient.pk, "doctor_id": self.doctor.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response2 = self.client.get(self.list_url)
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)
        
        url = reverse("mapping-detail-or-patient", kwargs={"pk": self.patient.pk})
        response3 = self.client.get(url)
        self.assertEqual(response3.status_code, status.HTTP_401_UNAUTHORIZED)
