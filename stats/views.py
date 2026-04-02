from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, Max, Count

from user.models import Player
from games.models import GameScore


def _get_player(request):
    if isinstance(request.user, Player):
        return request.user
    if request.auth and hasattr(request.auth, 'get'):
        try:
            return Player.objects.get(id=request.auth.get("user_id"))
        except Player.DoesNotExist:
            return None
    return None


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        player = _get_player(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)

        game_filter = request.query_params.get("game", "").strip()
        sort        = request.query_params.get("sort", "created_at")
        direction   = request.query_params.get("dir", "desc")
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        PAGE_SIZE = 20
        scores = GameScore.objects.filter(user=player)

        # ── overall ──────────────────────────────────────────────
        totals = scores.aggregate(
            total_games=Count("id"),
            total_points=Sum("score"),
            avg_score=Avg("score"),
            highest_score=Max("score"),
        )
        overall = {
            "total_games":   totals["total_games"]   or 0,
            "total_points":  totals["total_points"]  or 0,
            "avg_score":     round(totals["avg_score"] or 0, 1),
            "highest_score": totals["highest_score"] or 0,
        }

        # ── gameStats ─────────────────────────────────────────────
        game_stats = list(
            scores.values("game")
            .annotate(
                games_played=Count("id"),
                best_score=Max("score"),
                avg_score=Avg("score"),
                total_score=Sum("score"),
            )
            .order_by("-total_score")
        )
        for g in game_stats:
            g["avg_score"] = round(g["avg_score"] or 0, 1)

        # ── recentGames ───────────────────────────────────────────
        recent_games = list(
            scores.order_by("-created_at")
            .values("game", "score", "created_at")[:10]
        )

        # ── history (paginated, filterable, sortable) ─────────────
        history_qs = scores
        if game_filter:
            history_qs = history_qs.filter(game=game_filter)

        allowed_sorts = {"score", "created_at"}
        sort_field = sort if sort in allowed_sorts else "created_at"
        if direction == "asc":
            history_qs = history_qs.order_by(sort_field)
        else:
            history_qs = history_qs.order_by(f"-{sort_field}")

        history_total = history_qs.count()
        history_pages = max(1, (history_total + PAGE_SIZE - 1) // PAGE_SIZE)
        history = list(
            history_qs.values("game", "score", "created_at")
            [(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        )

        # ── distinctGames ─────────────────────────────────────────
        distinct_games = list(
            scores.values_list("game", flat=True).distinct().order_by("game")
        )

        return Response({
            "overall":       overall,
            "gameStats":     game_stats,
            "recentGames":   recent_games,
            "history":       history,
            "historyTotal":  history_total,
            "historyPages":  history_pages,
            "page":          page,
            "distinctGames": distinct_games,
        })
