from datetime import date as date_cls

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.bookings.services import available_slots
from apps.catalog.models import Service
from apps.common.exceptions import DomainError
from apps.common.permissions import IsCustomer, IsVendor, IsVerifiedVendor
from apps.search.services import search_vendors

from .models import Category, Favorite, ScheduleBlock, Vendor, WorkingHours
from .serializers import (
    CategorySerializer,
    FavoriteSerializer,
    ScheduleBlockSerializer,
    VendorDetailSerializer,
    VendorListSerializer,
    VendorProfileSerializer,
    VendorRegisterSerializer,
    VendorStatusSerializer,
    WorkingHoursSerializer,
)


class CategoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """FR-110 — browse categories (two-level hierarchy).

    ?top=true returns only top-level pillars (each with nested children);
    ?parent=<id|slug> returns the children of that parent.
    """

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        import uuid as uuid_lib

        qs = Category.objects.filter(is_active=True).prefetch_related("children")
        parent = self.request.query_params.get("parent")
        if parent:
            try:
                qs = qs.filter(parent_id=uuid_lib.UUID(parent))
            except ValueError:
                qs = qs.filter(parent__slug=parent)
        elif self.request.query_params.get("top") in ("true", "1"):
            qs = qs.filter(parent__isnull=True)
        return qs


def _parse_float(request, key):
    raw = request.query_params.get(key)
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValidationError({key: _("Must be a number.")}) from exc


class VendorViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Public vendor discovery (FR-111/112/113/114/140) + availability."""

    permission_classes = [AllowAny]

    def get_queryset(self):
        return Vendor.objects.select_related("category").prefetch_related(
            "services", "working_hours"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return VendorListSerializer
        return VendorDetailSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str),
            OpenApiParameter("category", str),
            OpenApiParameter("lat", float),
            OpenApiParameter("lng", float),
            OpenApiParameter("radius_km", float),
            OpenApiParameter("min_rating", float),
            OpenApiParameter("min_price", float),
            OpenApiParameter("max_price", float),
            OpenApiParameter("order_by", str, description="distance | rating | name"),
        ]
    )
    def list(self, request):
        qs = search_vendors(
            query=request.query_params.get("q"),
            category=request.query_params.get("category"),
            lat=_parse_float(request, "lat"),
            lng=_parse_float(request, "lng"),
            radius_km=_parse_float(request, "radius_km"),
            min_rating=_parse_float(request, "min_rating"),
            min_price=_parse_float(request, "min_price"),
            max_price=_parse_float(request, "max_price"),
            order_by=request.query_params.get("order_by", "distance"),
        )
        page = self.paginate_queryset(qs)
        serializer = VendorListSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="navigate")
    def navigate(self, request, pk=None):
        """FR-140 — return Google Maps / Waze deep links for the vendor."""
        vendor = get_object_or_404(Vendor, pk=pk)
        if vendor.location_lat is None or vendor.location_lng is None:
            raise DomainError(_("This vendor has no saved location."))
        lat, lng = vendor.location_lat, vendor.location_lng
        return Response(
            {
                "google_maps_url": f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}",
                "waze_url": f"https://waze.com/ul?ll={lat},{lng}&navigate=yes",
            }
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "services",
                str,
                required=True,
                description="Comma-separated service UUIDs ('service' also accepted)",
            ),
            OpenApiParameter("date", str, required=True, description="YYYY-MM-DD"),
        ]
    )
    @action(detail=True, methods=["get"], url_path="availability")
    def availability(self, request, pk=None):
        """Advisory list of bookable start times sized to the combined
        duration of the selected services."""
        vendor = get_object_or_404(Vendor, pk=pk)
        raw = request.query_params.get("services") or request.query_params.get("service")
        date_str = request.query_params.get("date")
        if not raw or not date_str:
            raise ValidationError(_("'services' and 'date' query params are required."))
        service_ids = [s.strip() for s in raw.split(",") if s.strip()]
        services = list(Service.objects.filter(pk__in=service_ids, vendor=vendor, is_active=True))
        if len(services) != len(set(service_ids)):
            raise ValidationError(_("One or more services not found for this vendor."))
        try:
            day = date_cls.fromisoformat(date_str)
        except ValueError as exc:
            raise ValidationError({"date": _("Use YYYY-MM-DD.")}) from exc
        slots = available_slots(vendor=vendor, services=services, date=day)
        return Response({"date": date_str, "slots": [s.isoformat() for s in slots]})


class VendorMeView(viewsets.ViewSet):
    """Vendor self-service: register + profile + status toggle."""

    permission_classes = [IsVendor]

    def _get_vendor(self, request):
        return getattr(request.user, "vendor", None)

    @extend_schema(responses=VendorProfileSerializer)
    def retrieve(self, request):
        vendor = self._get_vendor(request)
        if vendor is None:
            return Response(
                {"detail": _("No vendor profile yet.")}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(VendorProfileSerializer(vendor).data)

    @extend_schema(request=VendorRegisterSerializer, responses=VendorProfileSerializer)
    def create(self, request):
        """FR-201 — register the vendor business profile (once per user)."""
        if self._get_vendor(request) is not None:
            raise DomainError(_("A vendor profile already exists for this account."))
        serializer = VendorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = serializer.save(owner=request.user)
        return Response(VendorProfileSerializer(vendor).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=VendorProfileSerializer, responses=VendorProfileSerializer)
    def partial_update(self, request):
        vendor = self._get_vendor(request)
        if vendor is None:
            raise DomainError(_("Register a vendor profile first."))
        serializer = VendorProfileSerializer(vendor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(request=VendorStatusSerializer, responses=VendorProfileSerializer)
    @action(detail=False, methods=["patch"], url_path="status")
    def set_status(self, request):
        """FR-212 — toggle Open/Closed in real time."""
        vendor = self._get_vendor(request)
        if vendor is None:
            raise DomainError(_("Register a vendor profile first."))
        serializer = VendorStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor.status = serializer.validated_data["status"]
        vendor.save(update_fields=["status", "updated_at"])
        return Response(VendorProfileSerializer(vendor).data)


class AdminVendorViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """FR-301/204 — admin view/approve/suspend/remove vendors."""

    serializer_class = VendorProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["verification_status", "status", "category"]
    search_fields = ["business_name"]

    def get_queryset(self):
        return Vendor.objects.select_related("category", "owner").all()

    def _set_verification(self, request, pk, new_status):
        from apps.common.permissions import IsAdmin

        if not IsAdmin().has_permission(request, self):
            raise DomainError(_("Admin privileges required."))
        vendor = get_object_or_404(Vendor, pk=pk)
        vendor.verification_status = new_status
        vendor.save(update_fields=["verification_status", "updated_at"])
        return Response(VendorProfileSerializer(vendor).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .models import VerificationStatus

        return self._set_verification(request, pk, VerificationStatus.VERIFIED)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        from .models import VerificationStatus

        return self._set_verification(request, pk, VerificationStatus.SUSPENDED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .models import VerificationStatus

        return self._set_verification(request, pk, VerificationStatus.REJECTED)

    def get_permissions(self):
        from apps.common.permissions import IsAdmin

        return [IsAdmin()]


class WorkingHoursViewSet(viewsets.ModelViewSet):
    """FR-211 — vendor manages own working hours."""

    serializer_class = WorkingHoursSerializer
    permission_classes = [IsVerifiedVendor]
    pagination_class = None

    def get_queryset(self):
        return WorkingHours.objects.filter(vendor=getattr(self.request.user, "vendor", None))

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor)


class ScheduleBlockViewSet(viewsets.ModelViewSet):
    """FR-213 — vendor blocks dates/times."""

    serializer_class = ScheduleBlockSerializer
    permission_classes = [IsVerifiedVendor]

    def get_queryset(self):
        return ScheduleBlock.objects.filter(vendor=getattr(self.request.user, "vendor", None))

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor)


class FavoriteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Customer's server-synced favorite vendors.

    DELETE accepts the vendor id (not the favorite id) for app convenience.
    """

    serializer_class = FavoriteSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            "vendor", "vendor__category"
        )

    def perform_create(self, serializer):
        # Idempotent: re-favoriting an existing vendor is a no-op.
        Favorite.objects.get_or_create(
            user=self.request.user, vendor=serializer.validated_data["vendor"]
        )

    def destroy(self, request, pk=None):
        Favorite.objects.filter(user=request.user, vendor_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
