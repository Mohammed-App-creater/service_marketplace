from rest_framework import serializers

from apps.catalog.serializers import PublicServiceSerializer

from .models import Category, Favorite, ScheduleBlock, Vendor, WorkingHours


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "parent", "children"]
        read_only_fields = fields

    def get_children(self, obj):
        return [
            {"id": str(c.id), "name": c.name, "slug": c.slug, "icon": c.icon}
            for c in obj.children.all()
            if c.is_active
        ]


class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHours
        fields = ["id", "day_of_week", "open_time", "close_time", "is_closed"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        is_closed = attrs.get("is_closed", getattr(self.instance, "is_closed", False))
        open_time = attrs.get("open_time", getattr(self.instance, "open_time", None))
        close_time = attrs.get("close_time", getattr(self.instance, "close_time", None))
        if not is_closed:
            if open_time is None or close_time is None:
                raise serializers.ValidationError(
                    "Open and close times are required for an open day."
                )
            if close_time <= open_time:
                raise serializers.ValidationError("close_time must be after open_time.")
        return attrs


class ScheduleBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleBlock
        fields = ["id", "start_datetime", "end_datetime", "reason"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        start = attrs.get("start_datetime", getattr(self.instance, "start_datetime", None))
        end = attrs.get("end_datetime", getattr(self.instance, "end_datetime", None))
        if start and end and end <= start:
            raise serializers.ValidationError("end_datetime must be after start_datetime.")
        return attrs


class VendorListSerializer(serializers.ModelSerializer):
    """Compact card for search results (FR-113)."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "category",
            "category_name",
            "address",
            "location_lat",
            "location_lng",
            "status",
            "rating_avg",
            "rating_count",
            "cover_photo",
            "distance_km",
        ]

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance, 2) if distance is not None else None


class VendorDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    services = serializers.SerializerMethodField()
    working_hours = WorkingHoursSerializer(many=True, read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "category",
            "category_name",
            "description",
            "address",
            "location_lat",
            "location_lng",
            "contact_phone",
            "cover_photo",
            "status",
            "rating_avg",
            "rating_count",
            "services",
            "working_hours",
        ]

    def get_services(self, obj):
        active = obj.services.filter(is_active=True)
        return PublicServiceSerializer(active, many=True).data


class VendorRegisterSerializer(serializers.ModelSerializer):
    """FR-201 — vendor registers own business profile."""

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "category",
            "description",
            "address",
            "location_lat",
            "location_lng",
            "contact_phone",
            "cover_photo",
        ]
        read_only_fields = ["id"]


class VendorProfileSerializer(serializers.ModelSerializer):
    """Vendor viewing/editing its own profile (status fields read-only where appropriate)."""

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "category",
            "description",
            "address",
            "location_lat",
            "location_lng",
            "contact_phone",
            "cover_photo",
            "status",
            "verification_status",
            "rating_avg",
            "rating_count",
        ]
        read_only_fields = ["id", "verification_status", "rating_avg", "rating_count"]


class VendorStatusSerializer(serializers.Serializer):
    """FR-212 — Open/Closed toggle."""

    status = serializers.ChoiceField(choices=Vendor._meta.get_field("status").choices)


class FavoriteSerializer(serializers.ModelSerializer):
    vendor_detail = VendorListSerializer(source="vendor", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "vendor", "vendor_detail", "created_at"]
        read_only_fields = ["id", "vendor_detail", "created_at"]
