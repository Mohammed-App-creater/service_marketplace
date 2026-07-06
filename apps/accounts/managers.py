from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager supporting phone-OR-email identifiers."""

    use_in_migrations = True

    def _create_user(self, *, email=None, phone=None, password=None, **extra):
        if not email and not phone:
            raise ValidationError(_("Either an email or a phone number is required."))
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email or None, phone=phone or None, **extra)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email=None, phone=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email=email, phone=phone, password=password, **extra)

    def create_superuser(self, email=None, phone=None, password=None, **extra):
        from .models import Role

        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_active", True)
        extra.setdefault("is_email_verified", True)
        if extra.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self._create_user(email=email, phone=phone, password=password, **extra)

    def get_by_identifier(self, identifier):
        """Return the user matching an email or phone identifier, or None."""
        if not identifier:
            return None
        lookup = {"email__iexact": identifier} if "@" in identifier else {"phone": identifier}
        return self.filter(**lookup).first()
