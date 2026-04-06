from django.contrib import admin
from .models import Achievement, PlayerAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display  = ["id", "icon", "name", "condition_type", "condition_value", "game_specific"]
    list_filter   = ["condition_type"]
    search_fields = ["name", "game_specific"]


@admin.register(PlayerAchievement)
class PlayerAchievementAdmin(admin.ModelAdmin):
    list_display  = ["id", "player", "achievement", "earned_at"]
    ordering      = ["-earned_at"]
