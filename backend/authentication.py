from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings
from user.models import Player


class PlayerJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            player_id = validated_token["user_id"]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")
        try:
            return Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            raise AuthenticationFailed("User not found", code="user_not_found")


class PlayerInternalAuthentication(BaseAuthentication):
    """
    Authenticates internal Next.js → Django calls using a shared secret header.
    Next.js sends:
      X-Internal-Secret: <NEXTAUTH_INTERNAL_SECRET>
      X-Player-Id: <player id>
    """

    def authenticate(self, request):
        secret = request.META.get("HTTP_X_INTERNAL_SECRET", "")
        if not secret:
            return None  # Not an internal request — let other authenticators handle it

        expected = getattr(settings, "NEXTAUTH_INTERNAL_SECRET", "").strip()
        if not expected or secret.strip() != expected:
            raise AuthenticationFailed("Invalid internal secret.")

        player_id = request.META.get("HTTP_X_PLAYER_ID", "")
        if not player_id:
            raise AuthenticationFailed("Missing player ID.")

        try:
            player = Player.objects.get(id=int(player_id))
        except (Player.DoesNotExist, ValueError):
            raise AuthenticationFailed("Player not found.")

        return (player, None)
