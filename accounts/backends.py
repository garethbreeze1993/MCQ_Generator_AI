from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomBackend(BaseBackend):
    """
    Authenticate with username and password or email and password
    """

    def authenticate(self, request, username=None, password=None, **kwargs):

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user and user.check_password(password):
            return user

        return None


    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) else None


    def user_can_authenticate(self, user):
        # Mimics Django’s default backend check (e.g. user.is_active)
        return getattr(user, 'is_active', False)
