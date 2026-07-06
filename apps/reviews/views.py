from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, BookingStatus
from apps.common.permissions import IsCustomer, IsVendor

from .models import CustomerReview, Review
from .serializers import CustomerReviewSerializer, ReviewSerializer

User = get_user_model()


class ReviewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Create a review (FR-130); list a vendor's reviews (FR-131).

    Filter by vendor with ?vendor=<uuid>.
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ["vendor", "rating"]
    ordering_fields = ["created_at", "rating"]

    def get_queryset(self):
        return Review.objects.select_related("customer", "vendor").all()

    def get_permissions(self):
        if self.action == "create":
            return [IsCustomer()]
        return super().get_permissions()


class CustomerReviewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Vendor rates a customer after a completed booking.

    Filter by customer with ?customer=<uuid>.
    """

    serializer_class = CustomerReviewSerializer
    permission_classes = [IsVendor]
    filterset_fields = ["customer", "rating"]

    def get_queryset(self):
        return CustomerReview.objects.select_related("vendor", "customer").all()


class CustomerProfileView(APIView):
    """Customer profile as seen by a vendor: rating, reviews, shared history."""

    permission_classes = [IsVendor]

    def get(self, request, pk=None):
        customer = get_object_or_404(User, pk=pk)
        agg = CustomerReview.objects.filter(customer=customer).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        reviews = CustomerReview.objects.filter(customer=customer).select_related("vendor")[:20]

        # Service history between this customer and the requesting vendor.
        vendor = getattr(request.user, "vendor", None)
        previous_services = []
        if vendor:
            previous_services = list(
                Booking.objects.filter(
                    customer=customer, vendor=vendor, status=BookingStatus.COMPLETED
                ).values_list("items__service_name", flat=True)
            )

        return Response(
            {
                "id": str(customer.id),
                "name": customer.full_name,
                "member_since": customer.date_joined.date().isoformat(),
                "rating_avg": round(agg["avg"], 2) if agg["avg"] else None,
                "rating_count": agg["count"],
                "reviews": CustomerReviewSerializer(reviews, many=True).data,
                "previous_services": [s for s in previous_services if s],
            }
        )
