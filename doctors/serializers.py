from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    # Accept a single full name from clients, and split into first/last.
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "name",
            "first_name",
            "last_name",
            "specialization",
            "experience_years",
            "email",
            "phone_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "first_name", "last_name", "created_at", "updated_at"]

    def validate_email(self, value: str | None) -> str | None:
        """
        Email is optional, but when provided it must be unique (case-insensitive).
        """
        if not value:
            return value
        qs = Doctor.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A doctor with this email already exists.")
        return value

    def create(self, validated_data):
        # Split full name into first and last name (naive split on first space)
        full_name = validated_data.pop("name")
        full_name = (full_name or "").strip()
        first_name = full_name
        last_name = ""
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)

        return Doctor.objects.create(
            first_name=first_name,
            last_name=last_name,
            **validated_data,
        )

    def update(self, instance, validated_data):
        """
        Allow updating the doctor's name via the write-only 'name' field.
        """
        full_name = validated_data.pop("name", None)
        if full_name is not None:
            full_name = full_name.strip()
            first_name = full_name
            last_name = ""
            if " " in full_name:
                first_name, last_name = full_name.split(" ", 1)
            instance.first_name = first_name
            instance.last_name = last_name

        return super().update(instance, validated_data)

