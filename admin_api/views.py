from django.db import connection
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from backend.rate_limit import rate_limit, get_client_ip
from backend.authentication import PlayerInternalAuthentication


def is_admin(request):
    """Check X-Admin-Secret header sent from Next.js admin routes."""
    from django.conf import settings
    secret = request.META.get("HTTP_X_INTERNAL_SECRET", "")
    expected = getattr(settings, "NEXTAUTH_INTERNAL_SECRET", "")
    return secret == expected


def admin_required(fn):
    def wrapper(self, request, *args, **kwargs):
        if not is_admin(request):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return fn(self, request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


class AdminPlayersView(APIView):
    @admin_required
    def get(self, request):
        page   = max(1, int(request.query_params.get("page", 1)))
        search = request.query_params.get("search", "").strip()
        limit  = 10
        offset = (page - 1) * limit

        with connection.cursor() as cur:
            if search:
                like = f"%{search}%"
                cur.execute(
                    "SELECT id, player_name, email, created_at, status FROM players "
                    "WHERE is_admin = FALSE AND (player_name LIKE %s OR email LIKE %s) "
                    "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    [like, like, limit, offset]
                )
                players = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
                cur.execute(
                    "SELECT COUNT(*) FROM players WHERE is_admin = FALSE AND (player_name LIKE %s OR email LIKE %s)",
                    [like, like]
                )
            else:
                cur.execute(
                    "SELECT id, player_name, email, created_at, status FROM players "
                    "WHERE is_admin = FALSE ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    [limit, offset]
                )
                players = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
                cur.execute("SELECT COUNT(*) FROM players WHERE is_admin = FALSE")

            total = cur.fetchone()[0]

        return Response({"players": players, "total": total, "page": page, "limit": limit})


class AdminBanView(APIView):
    @admin_required
    def post(self, request):
        player_id = request.data.get("player_id")
        if not player_id or not str(player_id).isdigit():
            return Response({"error": "Invalid player_id"}, status=status.HTTP_400_BAD_REQUEST)
        with connection.cursor() as cur:
            cur.execute("UPDATE players SET status = 'banned' WHERE id = %s AND is_admin = FALSE", [int(player_id)])
        return Response({"success": True})


class AdminUnbanView(APIView):
    @admin_required
    def post(self, request):
        player_id = request.data.get("player_id")
        if not player_id or not str(player_id).isdigit():
            return Response({"error": "Invalid player_id"}, status=status.HTTP_400_BAD_REQUEST)
        with connection.cursor() as cur:
            cur.execute("UPDATE players SET status = 'active' WHERE id = %s AND is_admin = FALSE", [int(player_id)])
        return Response({"success": True})


class AdminDeleteView(APIView):
    @admin_required
    def post(self, request):
        player_id = request.data.get("player_id")
        if not player_id or not str(player_id).isdigit():
            return Response({"error": "Invalid player_id"}, status=status.HTTP_400_BAD_REQUEST)
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE players SET status = 'deleted' WHERE id = %s AND is_admin = FALSE",
                [int(player_id)]
            )
        return Response({"success": True})


class AdminRestoreView(APIView):
    @admin_required
    def post(self, request):
        player_id = request.data.get("player_id")
        if not player_id or not str(player_id).isdigit():
            return Response({"error": "Invalid player_id"}, status=status.HTTP_400_BAD_REQUEST)
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE players SET status = 'active' WHERE id = %s AND is_admin = FALSE",
                [int(player_id)]
            )
        return Response({"success": True})


class AdminEditView(APIView):
    @admin_required
    def post(self, request):
        player_id   = request.data.get("player_id")
        player_name = (request.data.get("player_name") or "").strip()
        email       = (request.data.get("email") or "").strip().lower()

        if not player_id or not str(player_id).isdigit():
            return Response({"error": "Invalid player_id"}, status=status.HTTP_400_BAD_REQUEST)
        if not player_name or not email:
            return Response({"error": "player_name and email are required"}, status=status.HTTP_400_BAD_REQUEST)

        with connection.cursor() as cur:
            cur.execute(
                "UPDATE players SET player_name = %s, email = %s WHERE id = %s AND is_admin = FALSE",
                [player_name, email, int(player_id)]
            )
        return Response({"success": True})


class AdminStatsView(APIView):
    @admin_required
    def get(self, request):
        data_points, labels = [], []
        with connection.cursor() as cur:
            for i in range(6, -1, -1):
                d = (timezone.now() - timedelta(days=i)).date()
                labels.append(d.strftime("%a, %b %-d") if hasattr(d, "strftime") else str(d))
                cur.execute("SELECT COUNT(*) FROM players WHERE DATE(created_at) = %s", [str(d)])
                data_points.append(cur.fetchone()[0])

            cur.execute(
                "SELECT activity, created_at, player_name FROM activity_logs "
                "ORDER BY created_at DESC LIMIT 100"
            )
            cols = [c[0] for c in cur.description]
            activity_logs = [dict(zip(cols, row)) for row in cur.fetchall()]

        total_new = sum(data_points)
        avg       = round((total_new / 7) * 10) / 10
        peak      = max(data_points) if data_points else 0
        best_day  = labels[data_points.index(peak)] if peak else "N/A"

        return Response({
            "dataPoints":    data_points,
            "labels":        labels,
            "totalNew":      total_new,
            "avg":           avg,
            "peak":          peak,
            "bestDay":       best_day,
            "activityLogs":  activity_logs,
        })


class AdminLeaderboardView(APIView):
    @admin_required
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT l.player_name, SUM(l.score) as total_score, COUNT(*) as total_games, "
                "MAX(l.created_at) as last_played "
                "FROM leaderboard l JOIN players p ON l.user_id = p.id "
                "WHERE p.is_admin = FALSE GROUP BY l.player_name "
                "ORDER BY total_score DESC LIMIT 20"
            )
            cols = [c[0] for c in cur.description]
            players = [dict(zip(cols, row)) for row in cur.fetchall()]
        return Response({"players": players})


class AdminGameStatsView(APIView):
    @admin_required
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT game, COUNT(*) as total_plays, COUNT(DISTINCT user_id) as unique_players, "
                "MAX(score) as highest_score, AVG(score) as avg_score "
                "FROM leaderboard GROUP BY game ORDER BY total_plays DESC"
            )
            cols = [c[0] for c in cur.description]
            games = [dict(zip(cols, row)) for row in cur.fetchall()]
        return Response({"games": games})
