from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # For create/update requests: a single full name field.
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "first_name",
            "last_name",
            "age",
            "gender",
            "address",
            "medical_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "first_name", "last_name", "created_at", "updated_at"]

    def validate_gender(self, value: str) -> str:
        """
        Accept common variants like 'Male', 'M', 'female', 'F', etc. (case-insensitive)
        and normalize them to the model's lowercase choices.
        """
        if value is None:
            return value
        normalized = value.strip().lower()

        if normalized in {"m", "male"}:
            return "male"
        if normalized in {"f", "female"}:
            return "female"
        if normalized in {"o", "other"}:
            return "other"

        raise serializers.ValidationError(
            'Gender must be one of: "male", "female", "other" (case-insensitive, '
            'or single-letter "M", "F", "O").'
        )

    def validate_age(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("Age must be a positive integer.")
        if value > 130:
            raise serializers.ValidationError("Age seems unrealistic.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Split full name into first and last name (naive split on first space)
        full_name = validated_data.pop("name")
        full_name = (full_name or "").strip()
        first_name = full_name
        last_name = ""
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)

        medical_history = validated_data.pop("medical_history", "")

        return Patient.objects.create(
            created_by=user,
            first_name=first_name,
            last_name=last_name,
            medical_history=medical_history,
            **validated_data,
        )

    def update(self, instance, validated_data):
        """
        Allow updating the patient's name via the write-only 'name' field,
        splitting into first_name and last_name. Other fields (age, gender,
        address, medical_history, etc.) are updated normally.
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

        # Let ModelSerializer handle the remaining fields
        return super().update(instance, validated_data)

