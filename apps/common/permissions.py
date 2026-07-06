"""Role- and ownership-based DRF permissions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role


class IsCustomer(BasePermission):
    message = "Only customers may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == Role.CUSTOMER
        )


class IsVendor(BasePermission):
    message = "Only vendors may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == Role.VENDOR
        )


class IsAdmin(BasePermission):
    message = "Only administrators may perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == Role.ADMIN or request.user.is_staff)
        )


class IsVerifiedVendor(BasePermission):
    """Vendor whose profile has been admin-verified (FR-204)."""

    message = "Your vendor profile must be verified before performing this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == Role.VENDOR):
            return False
        vendor = getattr(user, "vendor", None)
        return bool(vendor and vendor.is_verified)


class IsOwnerOrReadOnly(BasePermission):
    """Object-level: safe methods for anyone, writes only for the owner.

    Assumes the object exposes an ``owner`` attribute or ``owner_field`` on the view.
    """

    owner_field = "owner"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_field = getattr(view, "owner_field", self.owner_field)
        owner = getattr(obj, owner_field, None)
        return owner == request.user
