from django.db import models
from user.models import Player


class DailyChallenge(models.Model):
    challenge_date = models.DateField(unique=True)
    game           = models.CharField(max_length=100)
    title          = models.CharField(max_length=200)
    description    = models.TextField()
    target_type    = models.CharField(max_length=50, default="win")
    target_value   = models.IntegerField(default=1)
    bonus_points   = models.IntegerField(default=50)

    class Meta:
        db_table = "daily_challenges"
        managed  = False


class DailyChallengeCompletion(models.Model):
    user      = models.ForeignKey(Player, on_delete=models.CASCADE, db_column="user_id")
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, db_column="challenge_id")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "daily_challenge_completions"
        unique_together = (("user", "challenge"),)
        managed         = False


class GameScore(models.Model):
    user        = models.ForeignKey(Player, on_delete=models.CASCADE, db_column="user_id")
    player_name = models.CharField(max_length=100)
    game        = models.CharField(max_length=100)
    score       = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leaderboard"
        managed  = False

    def __str__(self):
        return f"{self.player_name} — {self.game}: {self.score}"


class FavoriteGame(models.Model):
    user       = models.ForeignKey(Player, on_delete=models.CASCADE, db_column="user_id")
    game       = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "favorite_games"
        unique_together = (("user", "game"),)
        managed         = False


class FavoriteWord(models.Model):
    user       = models.ForeignKey(Player, on_delete=models.CASCADE, db_column="user_id")
    word       = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "favorite_words"
        unique_together = (("user", "word"),)
        managed         = False


class ActivityLog(models.Model):
    player_name = models.CharField(max_length=100)
    activity    = models.CharField(max_length=255)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        managed  = False
