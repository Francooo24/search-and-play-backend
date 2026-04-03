from django.urls import path
from .views import (
    RegisterView, VerifyOtpView, LoginView, ProfileView,
    ChangePasswordView, ForgotPasswordView, ResetPasswordView,
    TokenRefreshView, ResendOtpView,
)

urlpatterns = [
    path("register/",        RegisterView.as_view(),       name="register"),
    path("verify-otp/",      VerifyOtpView.as_view(),      name="verify_otp"),
    path("resend-otp/",      ResendOtpView.as_view(),      name="resend_otp"),
    path("login/",           LoginView.as_view(),           name="login"),
    path("token/refresh/",   TokenRefreshView.as_view(),    name="token_refresh"),
    path("profile/",         ProfileView.as_view(),         name="profile"),
    path("change-password/", ChangePasswordView.as_view(),  name="change_password"),
    path("forgot-password/", ForgotPasswordView.as_view(),  name="forgot_password"),
    path("reset-password/",  ResetPasswordView.as_view(),   name="reset_password"),
]
