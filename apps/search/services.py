"""Vendor search & proximity query layer.

Simple lat/lng + Haversine (no PostGIS) — right-sized for a single-city MVP
(~200 vendors, <2s NFR). Callers depend only on ``search_vendors`` so a later
PostGIS/PointField swap is insulated to this module.
"""

import math

from django.db.models import F, FloatField, Q, Value
from django.db.models.functions import ACos, Cast, Cos, Least, Radians, Sin

from apps.vendors.models import Vendor, VerificationStatus

EARTH_RADIUS_KM = 6371.0


def _haversine_annotation(lat, lng):
    """Great-circle distance (km) from (lat, lng) to each vendor's location.

    Uses ``Least(1, ...)`` to guard against floating-point domain errors in ACOS.
    """
    lat_rad = math.radians(float(lat))
    lng_val = float(lng)
    cos_lat = math.cos(lat_rad)
    sin_lat = math.sin(lat_rad)

    f = FloatField()
    # Cast Decimal lat/lng columns to float so the trig arithmetic stays float.
    vendor_lat = Cast(F("location_lat"), f)
    vendor_lng = Cast(F("location_lng"), f)
    vendor_lat_rad = Radians(vendor_lat)
    delta_lng_rad = Radians(vendor_lng - Value(lng_val, output_field=f))

    cos_central = Value(sin_lat, output_field=f) * Sin(vendor_lat_rad) + Value(
        cos_lat, output_field=f
    ) * Cos(vendor_lat_rad) * Cos(delta_lng_rad)
    return ACos(Least(Value(1.0, output_field=f), cos_central)) * Value(
        EARTH_RADIUS_KM, output_field=f
    )


def _bounding_box(lat, lng, radius_km):
    lat = float(lat)
    lng = float(lng)
    lat_delta = radius_km / 111.0
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    lng_delta = radius_km / (111.0 * cos_lat)
    return (lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta)


def search_vendors(
    *,
    query=None,
    category=None,
    lat=None,
    lng=None,
    radius_km=None,
    min_rating=None,
    min_price=None,
    max_price=None,
    order_by="distance",
):
    """Return a queryset of live vendors matching the filters.

    Only verified vendors are ever returned (FR-204). When lat/lng are provided,
    results are annotated with ``distance`` (km) and can be ordered by proximity
    (FR-112).
    """
    qs = Vendor.objects.filter(verification_status=VerificationStatus.VERIFIED).select_related(
        "category"
    )

    if category:
        import uuid as uuid_lib

        try:
            qs = qs.filter(category_id=uuid_lib.UUID(str(category)))
        except ValueError:
            qs = qs.filter(category__slug=category)

    if query:
        qs = qs.filter(
            Q(business_name__icontains=query)
            | Q(services__name__icontains=query)
            | Q(category__name__icontains=query)
        ).distinct()

    if min_rating is not None:
        qs = qs.filter(rating_avg__gte=min_rating)

    if min_price is not None:
        qs = qs.filter(services__price__gte=min_price).distinct()
    if max_price is not None:
        qs = qs.filter(services__price__lte=max_price).distinct()

    has_location = lat is not None and lng is not None
    if has_location:
        if radius_km:
            lat_min, lat_max, lng_min, lng_max = _bounding_box(lat, lng, radius_km)
            qs = qs.filter(
                location_lat__gte=lat_min,
                location_lat__lte=lat_max,
                location_lng__gte=lng_min,
                location_lng__lte=lng_max,
            )
        qs = qs.annotate(distance=_haversine_annotation(lat, lng))

    # Ordering
    if order_by == "rating":
        qs = qs.order_by("-rating_avg", "-rating_count")
    elif order_by == "distance" and has_location:
        qs = qs.order_by("distance")
    else:
        qs = qs.order_by("business_name")

    return qs
