from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 (re-exported in urls)

from apps.common.exceptions import DomainError

from . import otp as otp_service
from .models import OTPPurpose
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """FR-101/102 — register and send a verification OTP."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def perform_create(self, serializer):
        from django.conf import settings

        user = serializer.save()
        if settings.AUTO_VERIFY_NEW_ACCOUNTS:
            return  # already active — no verification round-trip needed
        purpose = OTPPurpose.PHONE_VERIFY if user.phone else OTPPurpose.EMAIL_VERIFY
        otp_service.issue_otp(user, purpose)


class VerifyOTPView(APIView):
    """FR-102 — verify account via OTP."""

    permission_classes = [AllowAny]
    throttle_scope = "otp"

    @extend_schema(request=VerifyOTPSerializer, responses={200: None})
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get_by_identifier(serializer.validated_data["identifier"])
        if user is None:
            raise DomainError(_("No account for that identifier."))
        otp_service.verify_otp(
            user,
            serializer.validated_data["purpose"],
            serializer.validated_data["code"],
        )
        return Response({"detail": _("Verification successful.")}, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    @extend_schema(request=ResendOTPSerializer, responses={200: None})
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get_by_identifier(serializer.validated_data["identifier"])
        if user is not None:
            otp_service.issue_otp(user, serializer.validated_data["purpose"])
        # Do not reveal account existence.
        return Response({"detail": _("If the account exists, a code has been sent.")})


class LoginView(APIView):
    """FR-103 — obtain JWT access/refresh."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            {
                "access": data["access"],
                "refresh": data["refresh"],
                "user": UserSerializer(data["user"], context={"request": request}).data,
            }
        )


class LogoutView(APIView):
    """FR-103 — blacklist the refresh token."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordResetRequestView(APIView):
    """FR-104 — request a reset code."""

    permission_classes = [AllowAny]
    throttle_scope = "otp"

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get_by_identifier(serializer.validated_data["identifier"])
        if user is not None:
            otp_service.issue_otp(user, OTPPurpose.PASSWORD_RESET)
        return Response({"detail": _("If the account exists, a reset code has been sent.")})


class PasswordResetConfirmView(APIView):
    """FR-104 — confirm reset with code + new password."""

    permission_classes = [AllowAny]
    throttle_scope = "otp"

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get_by_identifier(serializer.validated_data["identifier"])
        if user is None:
            raise DomainError(_("No account for that identifier."))
        otp_service.verify_otp(user, OTPPurpose.PASSWORD_RESET, serializer.validated_data["code"])
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": _("Password updated.")})


class MeView(generics.RetrieveUpdateAPIView):
    """FR-105 — view/edit own profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
