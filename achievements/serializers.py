from rest_framework import serializers
from .models import Achievement, PlayerAchievement


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Achievement
        fields = ["id", "icon", "name", "description"]


class PlayerAchievementSerializer(serializers.ModelSerializer):
    icon        = serializers.CharField(source="achievement.icon")
    name        = serializers.CharField(source="achievement.name")
    description = serializers.CharField(source="achievement.description")

    class Meta:
        model  = PlayerAchievement
        fields = ["icon", "name", "description", "earned_at"]
