from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import DomainError
from apps.common.permissions import IsAdmin, IsVendor

from . import services as subscription_services
from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer, VendorSubscriptionSerializer


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Public list/read of plans; admin-only writes (FR-303)."""

    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticatedOrReadOnly()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "retrieve") and not (
            self.request.user.is_authenticated and self.request.user.is_staff
        ):
            qs = qs.filter(is_active=True)
        return qs


class VendorSubscriptionView(APIView):
    """FR-202/203 — the vendor's own subscription: view + choose/upgrade/downgrade."""

    permission_classes = [IsVendor]

    def _vendor(self, request):
        vendor = getattr(request.user, "vendor", None)
        if vendor is None:
            raise DomainError(_("Register a vendor profile first."))
        return vendor

    @extend_schema(responses=VendorSubscriptionSerializer)
    def get(self, request):
        vendor = self._vendor(request)
        sub = getattr(vendor, "subscription", None)
        if sub is None:
            return Response({"detail": _("No active subscription.")}, status=404)
        return Response(VendorSubscriptionSerializer(sub).data)

    @extend_schema(request=VendorSubscriptionSerializer, responses=VendorSubscriptionSerializer)
    def patch(self, request):
        vendor = self._vendor(request)
        serializer = VendorSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(
            SubscriptionPlan, id=serializer.validated_data["plan"].id, is_active=True
        )
        sub = subscription_services.set_vendor_plan(vendor, plan)
        return Response(VendorSubscriptionSerializer(sub).data)
