from rest_framework import viewsets, permissions

from .models import Doctor
from .serializers import DoctorSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer
    queryset = Doctor.objects.all()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        """
        Treat PUT as a partial update so clients can send only the fields
        they want to change on a doctor record.
        """
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

