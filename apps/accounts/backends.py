from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class PhoneOrEmailBackend(ModelBackend):
    """Authenticate with an ``identifier`` that is either an email or a phone."""

    def authenticate(self, request, identifier=None, password=None, **kwargs):
        User = get_user_model()
        if identifier is None:
            identifier = kwargs.get("username")
        if identifier is None or password is None:
            return None
        user = User.objects.get_by_identifier(identifier)
        if user is None:
            # Run the default hasher once to mitigate timing attacks.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
