from rest_framework import serializers
from .models import GameScore


class GameScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GameScore
        fields = ["id", "player_name", "game", "score", "created_at"]
        read_only_fields = ["id", "player_name", "created_at"]


class SubmitScoreSerializer(serializers.Serializer):
    game  = serializers.CharField(max_length=100)
    score = serializers.IntegerField(min_value=0, max_value=1_000_000)
    won   = serializers.BooleanField(default=True)
