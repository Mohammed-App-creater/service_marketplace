from datetime import date as date_cls

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.permissions import IsAdmin, IsCustomer, IsVendor

from . import services as booking_services
from .models import Booking, CancelledBy
from .serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingDeclineSerializer,
    BookingSerializer,
)


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Customer bookings: create (FR-120/121/122), list own, cancel (FR-124)."""

    permission_classes = [IsCustomer]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return (
            Booking.objects.filter(customer=self.request.user)
            .select_related("vendor")
            .prefetch_related("items")
        )

    @extend_schema(request=BookingCreateSerializer, responses=BookingSerializer)
    def create(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.create_booking(
            customer=request.user,
            vendor_id=serializer.validated_data["vendor"],
            service_ids=serializer.validated_data["services"],
            scheduled_start=serializer.validated_data["scheduled_start"],
            notes=serializer.validated_data["notes"],
        )
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=BookingCancelSerializer, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.cancel_booking(
            booking, by=CancelledBy.CUSTOMER, reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)


class VendorBookingViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Vendor booking management: calendar (FR-222), accept/decline (FR-221),
    complete/no-show (FR-223)."""

    permission_classes = [IsVendor]
    serializer_class = BookingSerializer

    def get_queryset(self):
        vendor = getattr(self.request.user, "vendor", None)
        return (
            Booking.objects.filter(vendor=vendor)
            .select_related("customer")
            .prefetch_related("items")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, description="YYYY-MM-DD (inclusive)"),
            OpenApiParameter("to", str, description="YYYY-MM-DD (inclusive)"),
            OpenApiParameter("status", str),
        ]
    )
    def list(self, request):
        qs = self.get_queryset()
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        status_filter = request.query_params.get("status")
        try:
            if date_from:
                qs = qs.filter(scheduled_start__date__gte=date_cls.fromisoformat(date_from))
            if date_to:
                qs = qs.filter(scheduled_start__date__lte=date_cls.fromisoformat(date_to))
        except ValueError as exc:
            raise ValidationError(_("Dates must be YYYY-MM-DD.")) from exc
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("scheduled_start")
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(BookingSerializer(page, many=True).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        booking = booking_services.accept_booking(booking)
        return Response(BookingSerializer(booking).data)

    @extend_schema(request=BookingDeclineSerializer, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = BookingDeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.decline_booking(
            booking, reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        booking = booking_services.mark_completed(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        booking = booking_services.mark_no_show(booking)
        return Response(BookingSerializer(booking).data)


class AdminBookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """FR-302 — admin views all bookings and resolves disputes."""

    permission_classes = [IsAdmin]
    serializer_class = BookingSerializer
    filterset_fields = ["status", "vendor", "customer"]

    def get_queryset(self):
        return Booking.objects.select_related("customer", "vendor").prefetch_related("items").all()

    @extend_schema(request=BookingCancelSerializer, responses=BookingSerializer)
    @action(detail=True, methods=["post"], url_path="resolve-cancel")
    def resolve_cancel(self, request, pk=None):
        """Admin dispute resolution: force-cancel a booking."""
        booking = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.admin_force_cancel(
            booking, reason=serializer.validated_data["reason"]
        )
        return Response(BookingSerializer(booking).data)
