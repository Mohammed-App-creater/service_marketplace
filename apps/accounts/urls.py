from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/resend-otp/", views.ResendOTPView.as_view(), name="resend-otp"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/password/reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "auth/password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("me/", views.MeView.as_view(), name="me"),
]
