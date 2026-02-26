from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import PatientDoctorMapping
from .serializers import PatientDoctorMappingSerializer
from patients.models import Patient


class PatientDoctorMappingListCreateView(generics.ListCreateAPIView):
    """
    POST /api/mappings/ - Assign a doctor to a patient.
    GET /api/mappings/ - Retrieve all patient-doctor mappings for the authenticated user.
    """

    serializer_class = PatientDoctorMappingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only mappings for patients created by the current user
        return PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)


class PatientDoctorMappingDetailAndPatientDoctorsView(generics.GenericAPIView):
    """
    Combined view to match the required API spec:

    - GET /api/mappings/<patient_id>/  -> all doctors assigned to that patient
    - DELETE /api/mappings/<id>/       -> delete a specific mapping by its id
    """

    serializer_class = PatientDoctorMappingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)

    def get(self, request, pk: int, *args, **kwargs):
        # Treat pk as patient_id
        try:
            patient = Patient.objects.get(pk=pk, created_by=request.user)
        except Patient.DoesNotExist:
            return Response({"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        mappings = self.get_queryset().filter(patient=patient)
        serializer = self.get_serializer(mappings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int, *args, **kwargs):
        # Treat pk as mapping id
        try:
            mapping = self.get_queryset().get(pk=pk)
        except PatientDoctorMapping.DoesNotExist:
            return Response({"detail": "Mapping not found."}, status=status.HTTP_404_NOT_FOUND)

        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

