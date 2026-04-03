from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Max, Count

from user.models import Player
from games.models import GameScore
from .models import Achievement, PlayerAchievement
from .serializers import PlayerAchievementSerializer


def _get_player(request):
    if isinstance(request.user, Player):
        return request.user
    if request.auth and hasattr(request.auth, 'get'):
        try:
            return Player.objects.get(id=request.auth.get("user_id"))
        except Player.DoesNotExist:
            return None
    return None


def _check_streak(scores, min_score, streak_len):
    recent = list(scores.order_by("-created_at").values_list("score", flat=True)[:streak_len])
    return len(recent) >= streak_len and all(s >= min_score for s in recent)


def _is_earned(achievement, scores, player=None):
    ct  = achievement.condition_type
    val = achievement.condition_value
    gs  = achievement.game_specific

    qs = scores.filter(game=gs) if gs else scores

    if ct == "games_played":
        return qs.count() >= val
    if ct == "wins":
        return qs.filter(score__gt=0).count() >= val
    if ct == "game_wins":
        return qs.filter(score__gt=0).count() >= val
    if ct == "streak":
        return _check_streak(qs, 1, val)
    if ct == "score":
        return scores.filter(score__gte=val, game=gs).exists() if gs else scores.filter(score__gte=val).exists()
    if ct == "total_points":
        total = (scores.aggregate(Sum("score"))["score__sum"] or 0)
        return total >= val
    if ct == "searches":
        from games.models import ActivityLog
        if not player:
            return False
        count = ActivityLog.objects.filter(
            player_name=player.player_name,
            activity__icontains='Searched for'
        ).count()
        return count >= val
    if ct == "favorites":
        from games.models import FavoriteWord
        if not player:
            return False
        return FavoriteWord.objects.filter(user=player).count() >= val
    # unknown condition type — do not award
    return False


class AchievementsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        player = _get_player(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)
        earned = PlayerAchievement.objects.filter(player=player).select_related("achievement")
        return Response(PlayerAchievementSerializer(earned, many=True).data)


class CheckAchievementsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"newAchievements": []})

        scores  = GameScore.objects.filter(user=player)
        already = set(
            PlayerAchievement.objects.filter(player=player)
            .values_list("achievement_id", flat=True)
        )

        new_badges = []
        for achievement in Achievement.objects.exclude(id__in=already):
            try:
                if _is_earned(achievement, scores, player=player):
                    PlayerAchievement.objects.get_or_create(player=player, achievement=achievement)
                    new_badges.append({
                        "icon":        achievement.icon,
                        "name":        achievement.name,
                        "description": achievement.description,
                    })
            except Exception:
                continue

        return Response({"newAchievements": new_badges})
