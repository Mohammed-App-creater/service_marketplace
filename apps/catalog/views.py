from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.common.permissions import IsVerifiedVendor

from .models import Service, ServiceImage
from .serializers import ServiceImageSerializer, ServiceSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    """Vendor-owned Service CRUD (FR-210), incl. discounts and gallery images."""

    serializer_class = ServiceSerializer
    permission_classes = [IsVerifiedVendor]

    def get_queryset(self):
        vendor = getattr(self.request.user, "vendor", None)
        return Service.objects.filter(vendor=vendor).prefetch_related("images")

    def perform_create(self, serializer):
        vendor = self.request.user.vendor
        plan = getattr(getattr(vendor, "subscription", None), "plan", None)
        if plan and plan.max_services is not None:
            if Service.objects.filter(vendor=vendor).count() >= plan.max_services:
                raise ValidationError(
                    _("Your plan allows at most %(n)s services.") % {"n": plan.max_services}
                )
        serializer.save(vendor=vendor)

    @extend_schema(request=ServiceImageSerializer, responses=ServiceImageSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser],
    )
    def add_image(self, request, pk=None):
        """Upload a gallery image (multipart: image, optional position)."""
        service = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ServiceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(service=service)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"images/(?P<image_id>[^/.]+)",
    )
    def remove_image(self, request, pk=None, image_id=None):
        service = get_object_or_404(self.get_queryset(), pk=pk)
        image = get_object_or_404(ServiceImage, pk=image_id, service=service)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
