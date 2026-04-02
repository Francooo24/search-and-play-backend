from rest_framework import serializers
import bcrypt
from .models import Player, PendingVerification


class RegisterSerializer(serializers.Serializer):
    player_name = serializers.CharField(max_length=100, min_length=2)
    email       = serializers.EmailField(max_length=255)
    password    = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)
    birthdate   = serializers.DateField()
    show_kids   = serializers.BooleanField(default=False)
    show_teen   = serializers.BooleanField(default=False)
    show_adult  = serializers.BooleanField(default=False)

    def validate_email(self, value):
        if Player.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp   = serializers.CharField(max_length=6, min_length=6)


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            player = Player.objects.get(email=data["email"])
        except Player.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")

        if not bcrypt.checkpw(data["password"].encode(), player.password.encode()):
            raise serializers.ValidationError("Invalid email or password.")

        if player.status == "banned":
            raise serializers.ValidationError("Your account has been banned.")

        data["player"] = player
        return data


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Player
        fields = ["id", "player_name", "email", "birthdate", "show_kids", "show_teen", "show_adult", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        player = self.context["request"].user_player
        if not bcrypt.checkpw(value.encode(), player.password.encode()):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)


class ResetPasswordSerializer(serializers.Serializer):
    email    = serializers.EmailField(max_length=255)
    otp      = serializers.RegexField(r'^\d{6}$', max_length=6)
    password = serializers.CharField(write_only=True, min_length=6, max_length=128)
