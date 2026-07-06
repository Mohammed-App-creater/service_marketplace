from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsAdmin

from .models import Complaint
from .serializers import ComplaintResolveSerializer, ComplaintSerializer


class ComplaintViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """File and track own complaints (customer or vendor)."""

    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        return Complaint.objects.filter(complainant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(complainant=self.request.user)


class AdminComplaintViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Admin review and resolution of complaints."""

    serializer_class = ComplaintSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["status", "target_vendor"]

    def get_queryset(self):
        return Complaint.objects.select_related("complainant", "target_vendor").all()

    @extend_schema(request=ComplaintResolveSerializer, responses=ComplaintSerializer)
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        complaint = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ComplaintResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint.status = serializer.validated_data["status"]
        complaint.resolution_note = serializer.validated_data["resolution_note"]
        complaint.save(update_fields=["status", "resolution_note", "updated_at"])
        return Response(ComplaintSerializer(complaint).data)
