import random
import secrets
import bcrypt
from datetime import timedelta

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from backend.rate_limit import rate_limit, get_client_ip
from .models import Player, PendingVerification, PasswordReset
from .serializers import (
    RegisterSerializer, VerifyOtpSerializer,
    LoginSerializer, PlayerSerializer, ChangePasswordSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer,
)

RATE_LIMITED = Response(
    {"error": "Too many requests. Please wait and try again."},
    status=status.HTTP_429_TOO_MANY_REQUESTS,
)


class TokenRefreshView(APIView):
    """Custom token refresh — validates refresh token and issues a new access token."""
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"token_refresh:{ip}", max_requests=20, window_seconds=60):
            return RATE_LIMITED

        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            player_id = token.get("user_id")
            if not player_id:
                raise TokenError("Invalid token payload")

            # Verify player still exists and is not banned
            player = Player.objects.get(id=player_id)
            if getattr(player, "status", None) == "banned":
                return Response({"error": "Account is banned."}, status=status.HTTP_403_FORBIDDEN)

            # Issue new access token with correct claims
            new_access = RefreshToken()
            new_access["user_id"]     = player.id
            new_access["player_name"] = player.player_name
            new_access["is_admin"]    = False

            return Response({"access": str(new_access.access_token)})

        except Player.DoesNotExist:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)
        except TokenError as e:
            return Response({"error": f"Invalid or expired refresh token: {e}"}, status=status.HTTP_401_UNAUTHORIZED)


def get_tokens(player):
    refresh = RefreshToken()
    refresh["user_id"]     = player.id
    refresh["player_name"] = player.player_name
    refresh["is_admin"]    = False
    return {
        "refresh": str(refresh),
        "access":  str(refresh.access_token),
    }


def _get_player_from_request(request):
    if isinstance(request.user, Player):
        return request.user
    if request.auth and hasattr(request.auth, 'get'):
        try:
            return Player.objects.get(id=request.auth.get("user_id"))
        except Player.DoesNotExist:
            return None
    return None


class RegisterView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"register:{ip}", max_requests=5, window_seconds=600):
            return RATE_LIMITED
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Remove old pending entry for this email
        PendingVerification.objects.filter(email=data["email"]).delete()

        otp        = str(random.randint(100000, 999999))
        otp_expires = timezone.now() + timedelta(minutes=10)
        hashed_pw  = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

        PendingVerification.objects.create(
            player_name = data["player_name"],
            email       = data["email"],
            password    = hashed_pw,
            birthdate   = data["birthdate"],
            token       = secrets.token_hex(32),
            expires     = otp_expires,
            show_kids   = data.get("show_kids", False),
            show_teen   = data.get("show_teen", False),
            show_adult  = data.get("show_adult", False),
            country     = data.get("country", "") or None,
            otp         = otp,
            otp_expires = otp_expires,
        )

        # Send OTP email
        try:
            send_mail(
                subject="Your Search & Play Verification Code",
                message=f"Hi {data['player_name']},\n\nYour OTP code is: {otp}\n\nThis code expires in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[data["email"]],
                html_message=f"""
                <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;background:#0d0d14;color:#e2e8f0;border-radius:16px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#f97316,#fb923c);padding:24px;text-align:center;">
                        <h1 style="margin:0;color:#fff;font-size:24px;">Search &amp; Play</h1>
                    </div>
                    <div style="padding:32px;text-align:center;">
                        <p style="font-size:16px;margin-bottom:8px;">Hi <strong>{data['player_name']}</strong>,</p>
                        <p style="color:#94a3b8;margin-bottom:24px;">Enter this OTP code to verify your account:</p>
                        <div style="background:#1e1e2e;border:2px solid #f97316;border-radius:12px;padding:24px;display:inline-block;margin-bottom:24px;">
                            <span style="font-size:40px;font-weight:700;letter-spacing:12px;color:#f97316;">{otp}</span>
                        </div>
                        <p style="color:#64748b;font-size:13px;">This code expires in <strong>10 minutes</strong>.</p>
                        <p style="color:#64748b;font-size:13px;">If you did not sign up, ignore this email.</p>
                    </div>
                </div>
                """,
            )
        except Exception:
            PendingVerification.objects.filter(email=data["email"]).delete()
            return Response(
                {"error": "Failed to send verification email. Please check your email address."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"otp_pending": True, "pending_email": data["email"]}, status=status.HTTP_200_OK)


class VerifyOtpView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"verify_otp:{ip}", max_requests=10, window_seconds=600):
            return RATE_LIMITED
        serializer = VerifyOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        otp   = serializer.validated_data["otp"]

        try:
            pending = PendingVerification.objects.get(email=email, otp=otp)
        except PendingVerification.DoesNotExist:
            return Response({"error": "Invalid OTP code. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

        if pending.otp_expires < timezone.now():
            pending.delete()
            return Response({"error": "OTP has expired. Please sign up again."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the player
        player = Player.objects.create(
            player_name = pending.player_name,
            email       = pending.email,
            password    = pending.password,
            birthdate   = pending.birthdate,
            show_kids   = pending.show_kids,
            show_teen   = pending.show_teen,
            show_adult  = pending.show_adult,
            country     = pending.country,
        )

        pending.delete()

        return Response({"success": True, "message": "Account created successfully."}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"login:{ip}", max_requests=10, window_seconds=600):
            return RATE_LIMITED
        # Also rate limit by email to prevent targeted brute force
        email = (request.data.get("email") or "").strip().lower()
        if email and rate_limit(f"login_email:{email}", max_requests=10, window_seconds=600):
            return RATE_LIMITED
        # Internal call from NextAuth — skip password, just issue tokens by email
        if request.data.get("_nextauth"):
            secret = request.data.get("_secret", "")
            if secret != settings.NEXTAUTH_INTERNAL_SECRET:
                return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
            email = (request.data.get("email") or "").strip().lower()
            try:
                player = Player.objects.get(email=email)
                return Response({"tokens": get_tokens(player)})
            except Player.DoesNotExist:
                return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            player = serializer.validated_data["player"]
            tokens = get_tokens(player)
            return Response({
                "user":   PlayerSerializer(player).data,
                "tokens": tokens,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_player(self, request):
        return _get_player_from_request(request)

    def get(self, request):
        player = self._get_player(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlayerSerializer(player).data)

    def patch(self, request):
        player = self._get_player(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PlayerSerializer(player, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player_from_request(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)

        request.user_player = player
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            player.password = bcrypt.hashpw(serializer.validated_data["new_password"].encode(), bcrypt.gensalt()).decode()
            player.save()
            return Response({"message": "Password updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"forgot_password:{ip}", max_requests=5, window_seconds=600):
            return RATE_LIMITED
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        try:
            Player.objects.get(email=email)
        except Player.DoesNotExist:
            return Response({"error": "No account found with that email."}, status=status.HTTP_404_NOT_FOUND)

        otp     = str(random.randint(100000, 999999))
        expires = timezone.now() + timedelta(minutes=15)

        PasswordReset.objects.update_or_create(
            email=email,
            defaults={"token": otp, "expires_at": expires},
        )

        try:
            send_mail(
                subject="Your Password Reset Code – Search & Play",
                message=f"Your reset code is: {otp}\n\nExpires in 15 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=f"""
                <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#1a1a2e;color:#fff;border-radius:16px;">
                    <h2 style="color:#f97316;">Password Reset Code</h2>
                    <p style="color:#d1d5db;">Use the code below. It expires in <strong>15 minutes</strong>.</p>
                    <div style="text-align:center;margin:32px 0;">
                        <div style="display:inline-block;background:linear-gradient(to right,#f97316,#f59e0b);padding:16px 40px;border-radius:12px;font-size:2rem;font-weight:900;letter-spacing:0.3em;color:#fff;">{otp}</div>
                    </div>
                </div>
                """,
            )
        except Exception:
            return Response({"error": "Failed to send email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "OTP sent."})


class ResendOtpView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"resend_otp:{ip}", max_requests=3, window_seconds=600):
            return RATE_LIMITED

        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pending = PendingVerification.objects.get(email=email)
        except PendingVerification.DoesNotExist:
            return Response({"error": "No pending verification found. Please sign up again."}, status=status.HTTP_404_NOT_FOUND)

        otp         = str(random.randint(100000, 999999))
        otp_expires = timezone.now() + timedelta(minutes=10)
        pending.otp         = otp
        pending.otp_expires = otp_expires
        pending.save()

        try:
            send_mail(
                subject="Your New Search & Play Verification Code",
                message=f"Hi {pending.player_name},\n\nYour new OTP code is: {otp}\n\nThis code expires in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=f"""
                <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;background:#0d0d14;color:#e2e8f0;border-radius:16px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#f97316,#fb923c);padding:24px;text-align:center;">
                        <h1 style="margin:0;color:#fff;font-size:24px;">Search &amp; Play</h1>
                    </div>
                    <div style="padding:32px;text-align:center;">
                        <p style="font-size:16px;margin-bottom:8px;">Hi <strong>{pending.player_name}</strong>,</p>
                        <p style="color:#94a3b8;margin-bottom:24px;">Here is your new OTP code:</p>
                        <div style="background:#1e1e2e;border:2px solid #f97316;border-radius:12px;padding:24px;display:inline-block;margin-bottom:24px;">
                            <span style="font-size:40px;font-weight:700;letter-spacing:12px;color:#f97316;">{otp}</span>
                        </div>
                        <p style="color:#64748b;font-size:13px;">This code expires in <strong>10 minutes</strong>.</p>
                    </div>
                </div>
                """,
            )
        except Exception:
            return Response({"error": "Failed to send email. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"success": True})


class ResetPasswordView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        if rate_limit(f"reset_password:{ip}", max_requests=5, window_seconds=600):
            return RATE_LIMITED
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data  = serializer.validated_data
        email = data["email"].lower()
        otp   = data["otp"]

        try:
            record = PasswordReset.objects.get(email=email, token=otp)
        except PasswordReset.DoesNotExist:
            return Response({"error": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        if record.expires_at < timezone.now():
            record.delete()
            return Response({"error": "Code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        Player.objects.filter(email=email).update(password=hashed)
        record.delete()

        return Response({"message": "Password updated successfully."})
