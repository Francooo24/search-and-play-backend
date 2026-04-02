from django.contrib import admin
from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display  = ["id", "player_name", "email", "status", "created_at"]
    list_filter   = ["status"]
    search_fields = ["player_name", "email"]
    ordering      = ["-created_at"]
