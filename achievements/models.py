from django.db import models
from user.models import Player


class Achievement(models.Model):
    icon            = models.CharField(max_length=10)
    name            = models.CharField(max_length=100, unique=True)
    description     = models.CharField(max_length=255)
    condition_type  = models.CharField(max_length=50)
    condition_value = models.IntegerField(default=0)
    game_specific   = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "achievements"
        managed  = False

    def __str__(self):
        return self.name


class PlayerAchievement(models.Model):
    player      = models.ForeignKey(Player, on_delete=models.CASCADE, db_column="user_id")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, db_column="achievement_id")
    earned_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "player_achievements"
        unique_together = (("player", "achievement"),)
        managed         = False

    def __str__(self):
        return f"{self.player.player_name} — {self.achievement.name}"
