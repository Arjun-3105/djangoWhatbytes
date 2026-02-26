from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # Optional: can be sent by clients that want UI-level confirmation,
    # but is not required by the API.
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ["id", "email", "name", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        # Validate only if confirm password is provided and non-empty
        if password_confirm not in (None, "",):
            if password != password_confirm:
                raise serializers.ValidationError(
                    {"password_confirm": "Passwords do not match."}
                )

        return attrs


    def create(self, validated_data):
        # Ignore confirm field if present
        validated_data.pop("password_confirm", None)
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError(_("Unable to log in with provided credentials."))
        if not user.is_active:
            raise serializers.ValidationError(_("User account is disabled."))

        refresh = RefreshToken.for_user(user)
        return {
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }

