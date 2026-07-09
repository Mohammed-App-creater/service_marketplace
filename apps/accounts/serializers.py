from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPPurpose, Role
from .validators import validate_ethiopian_phone

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_null=True)
    phone = PhoneNumberField(
        required=False, allow_null=True, validators=[validate_ethiopian_phone]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(
        choices=[(Role.CUSTOMER, Role.CUSTOMER.label), (Role.VENDOR, Role.VENDOR.label)],
        default=Role.CUSTOMER,
    )

    class Meta:
        model = User
        fields = ["id", "email", "phone", "full_name", "password", "role", "preferred_language"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("An account with this email already exists."))
        return value

    def validate_phone(self, value):
        # value is already normalized to E.164 by PhoneNumberField.
        if value and User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                _("An account with this phone number already exists.")
            )
        return value

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError(_("Provide an email or a phone number."))
        return attrs

    def create(self, validated_data):
        from django.conf import settings

        password = validated_data.pop("password")
        if settings.AUTO_VERIFY_NEW_ACCOUNTS:
            # Dev/testing mode: active immediately, no OTP step needed.
            user = User.objects.create_user(
                password=password,
                is_active=True,
                is_phone_verified=bool(validated_data.get("phone")),
                is_email_verified=bool(validated_data.get("email")),
                **validated_data,
            )
        else:
            # New accounts start inactive until OTP/email verification (FR-102).
            user = User.objects.create_user(password=password, is_active=False, **validated_data)
        return user


class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=OTPPurpose.choices, default=OTPPurpose.PHONE_VERIFY)


class ResendOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    purpose = serializers.ChoiceField(choices=OTPPurpose.choices, default=OTPPurpose.PHONE_VERIFY)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            identifier=attrs["identifier"],
            password=attrs["password"],
        )
        if user is None:
            # authenticate() also rejects inactive users — tell them the real
            # reason when the password was right but the account is unverified.
            existing = User.objects.get_by_identifier(attrs["identifier"])
            if (
                existing is not None
                and existing.check_password(attrs["password"])
                and not existing.is_active
            ):
                raise serializers.ValidationError(
                    _("Account not verified. Verify the code sent to your phone/email, then log in.")
                )
            raise serializers.ValidationError(_("Invalid credentials."))
        refresh = RefreshToken.for_user(user)
        attrs["user"] = user
        attrs["access"] = str(refresh.access_token)
        attrs["refresh"] = str(refresh)
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = RefreshToken(attrs["refresh"])
        return attrs

    def save(self, **kwargs):
        self.token.blacklist()


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "role",
            "profile_photo",
            "preferred_language",
            "location_lat",
            "location_lng",
            "is_phone_verified",
            "is_email_verified",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "role",
            "is_phone_verified",
            "is_email_verified",
            "date_joined",
        ]
