from rest_framework import serializers

from .models import PatientDoctorMapping
from patients.models import Patient
from doctors.models import Doctor


class PatientDoctorMappingSerializer(serializers.ModelSerializer):
    # Expose both the related object (string) and their primary key IDs.
    # IDs are used for create/update; they are also returned in responses.
    patient_id = serializers.PrimaryKeyRelatedField(
        source="patient", queryset=Patient.objects.all()
    )
    doctor_id = serializers.PrimaryKeyRelatedField(
        source="doctor", queryset=Doctor.objects.all()
    )
    patient = serializers.StringRelatedField(read_only=True)
    doctor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = [
            "id",
            "patient_id",
            "doctor_id",
            "patient",
            "doctor",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "doctor", "created_at"]

    def validate(self, attrs):
        patient = attrs["patient"]
        doctor = attrs["doctor"]
        
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            if patient.created_by != request.user:
                raise serializers.ValidationError(
                    {"patient_id": "You do not have permission to assign to this patient."}
                )

        if PatientDoctorMapping.objects.filter(patient=patient, doctor=doctor).exists():
            raise serializers.ValidationError("This doctor is already assigned to the patient.")
        return attrs

