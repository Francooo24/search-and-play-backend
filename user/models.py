from django.db import models
from django.utils import timezone


class Player(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("banned", "Banned")]

    player_name = models.CharField(max_length=100)
    email       = models.EmailField(max_length=255, unique=True)
    password    = models.CharField(max_length=255)
    birthdate   = models.DateField(null=True, blank=True)
    show_kids   = models.BooleanField(default=False)
    show_teen   = models.BooleanField(default=False)
    show_adult  = models.BooleanField(default=False)
    country     = models.CharField(max_length=2, null=True, blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at  = models.DateTimeField(auto_now_add=True)

    # Required by DRF's IsAuthenticated permission check
    is_authenticated = True
    is_anonymous     = False

    class Meta:
        db_table = "players"
        managed  = False

    def __str__(self):
        return self.player_name


class PendingVerification(models.Model):
    player_name = models.CharField(max_length=100)
    email       = models.EmailField(max_length=255, unique=True)
    password    = models.CharField(max_length=255)
    birthdate   = models.DateField(null=True, blank=True)
    token       = models.CharField(max_length=64, unique=True, default='')
    expires     = models.DateTimeField(default=timezone.now)
    show_kids   = models.BooleanField(default=False)
    show_teen   = models.BooleanField(default=False)
    show_adult  = models.BooleanField(default=False)
    country     = models.CharField(max_length=2, null=True, blank=True)
    otp         = models.CharField(max_length=6, null=True, blank=True)
    otp_expires = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pending_verifications"
        managed  = False

    def __str__(self):
        return self.email


class PasswordReset(models.Model):
    email      = models.EmailField(max_length=255, primary_key=True)
    token      = models.CharField(max_length=64)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "password_resets"
        managed  = False
