from django.contrib import admin
from .models import GameScore, ActivityLog, DailyChallenge, DailyChallengeCompletion, FavoriteGame, FavoriteWord


@admin.register(GameScore)
class GameScoreAdmin(admin.ModelAdmin):
    list_display  = ["id", "player_name", "game", "score", "created_at"]
    list_filter   = ["game"]
    search_fields = ["player_name", "game"]
    ordering      = ["-created_at"]


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = ["id", "player_name", "activity", "created_at"]
    search_fields = ["player_name", "activity"]
    ordering      = ["-created_at"]


@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display  = ["id", "challenge_date", "game", "title", "bonus_points"]
    ordering      = ["-challenge_date"]
    search_fields = ["game", "title"]


@admin.register(DailyChallengeCompletion)
class DailyChallengeCompletionAdmin(admin.ModelAdmin):
    list_display  = ["id", "user", "challenge", "completed_at"]
    ordering      = ["-completed_at"]


@admin.register(FavoriteGame)
class FavoriteGameAdmin(admin.ModelAdmin):
    list_display  = ["id", "user", "game", "created_at"]
    search_fields = ["game"]
    ordering      = ["-created_at"]


@admin.register(FavoriteWord)
class FavoriteWordAdmin(admin.ModelAdmin):
    list_display  = ["id", "user", "word", "created_at"]
    search_fields = ["word"]
    ordering      = ["-created_at"]
