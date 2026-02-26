from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailAuthBackend(ModelBackend):
    """Authenticate users by email and password."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None
