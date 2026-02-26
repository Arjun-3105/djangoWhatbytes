from rest_framework import viewsets, permissions

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only allow users to see their own patients
        return Patient.objects.filter(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Treat PUT like a partial update so clients can send only the
        fields they want to change.
        """
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

