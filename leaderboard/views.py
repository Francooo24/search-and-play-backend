from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection

RANKING_TIERS = [
    {"name": "Novice",      "min": 0,     "max": 99,    "icon": "🌱", "color": "text-gray-400",   "bg": "bg-gray-500/10",   "border": "border-gray-500/30"},
    {"name": "Explorer",    "min": 100,   "max": 499,   "icon": "🗺️", "color": "text-blue-400",   "bg": "bg-blue-500/10",   "border": "border-blue-500/30"},
    {"name": "Adventurer",  "min": 500,   "max": 1499,  "icon": "⚔️", "color": "text-green-400",  "bg": "bg-green-500/10",  "border": "border-green-500/30"},
    {"name": "Champion",    "min": 1500,  "max": 4999,  "icon": "🏆", "color": "text-yellow-400", "bg": "bg-yellow-500/10", "border": "border-yellow-500/30"},
    {"name": "Master",      "min": 5000,  "max": 14999, "icon": "👑", "color": "text-orange-400", "bg": "bg-orange-500/10", "border": "border-orange-500/30"},
    {"name": "Grandmaster", "min": 15000, "max": 49999, "icon": "💎", "color": "text-purple-400", "bg": "bg-purple-500/10", "border": "border-purple-500/30"},
    {"name": "Legend",      "min": 50000, "max": 0,     "icon": "🌟", "color": "text-amber-400",  "bg": "bg-amber-500/10",  "border": "border-amber-500/30"},
]


def get_tier(pts):
    tier = next((t for t in reversed(RANKING_TIERS) if pts >= t["min"]), RANKING_TIERS[0])
    is_max   = tier["max"] == 0
    rng      = 1 if is_max else tier["max"] - tier["min"] + 1
    progress = 100 if is_max else min(100, round(((pts - tier["min"]) / rng) * 100))
    return tier, progress


class LeaderboardView(APIView):
    def get(self, request):
        view   = request.query_params.get("view", "leaderboard")
        game   = request.query_params.get("game", "").strip()
        period = request.query_params.get("period", "all")

        try:
            with connection.cursor() as cur:
                if view == "pergame":
                    cur.execute(
                        "SELECT l.game, l.player_name, MAX(l.score) as score, p.country "
                        "FROM leaderboard l JOIN players p ON l.user_id = p.id "
                        "WHERE p.is_admin = 0 GROUP BY l.game, l.player_name, p.country ORDER BY l.game, score DESC"
                    )
                    rows = cur.fetchall()
                    cur.execute(
                        "SELECT DISTINCT l.game FROM leaderboard l JOIN players p ON l.user_id = p.id "
                        "WHERE p.is_admin = 0 ORDER BY l.game"
                    )
                    game_list = [r[0] for r in cur.fetchall()]
                    games: dict = {}
                    for game_name, player_name, score, country in rows:
                        if game_name not in games:
                            games[game_name] = []
                        if len(games[game_name]) < 3:
                            games[game_name].append({"player_name": player_name, "score": score, "country": country})
                    return Response({"games": games, "game_list": game_list})

                if view == "game":
                    cur.execute(
                        "SELECT l.player_name, MAX(l.score) as best_score, COUNT(*) as plays, MAX(l.created_at) as last_played, p.country "
                        "FROM leaderboard l JOIN players p ON l.user_id = p.id "
                        "WHERE l.game = %s AND p.is_admin = 0 GROUP BY l.player_name, p.country ORDER BY best_score DESC LIMIT 10",
                        [game]
                    )
                    rows = cur.fetchall()
                    players = [{"player_name": r[0], "best_score": r[1], "plays": r[2], "last_played": str(r[3]), "country": r[4]} for r in rows]
                    return Response({"players": players})

                if view == "rankings":
                    age_filter = request.query_params.get("age_group", "").strip()
                    cur.execute(
                        "SELECT p.id, p.player_name, COALESCE(SUM(l.score),0) AS total_points, "
                        "COUNT(l.id) AS total_games, COALESCE(AVG(l.score),0) AS avg_score, MAX(l.created_at) AS last_played, p.birthdate, p.country "
                        "FROM players p LEFT JOIN leaderboard l ON p.id = l.user_id "
                        "WHERE p.is_admin = 0 "
                        "GROUP BY p.id, p.player_name, p.birthdate, p.country HAVING total_points > 0 ORDER BY total_points DESC LIMIT 50"
                    )
                    rows = cur.fetchall()
                    from datetime import date
                    today = date.today()
                    def get_age_group(birthdate):
                        if not birthdate: return None
                        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                        return "kids" if age <= 12 else "teen" if age <= 17 else "adult"
                    players = []
                    for r in rows:
                        pts = int(r[2])
                        tier, progress = get_tier(pts)
                        age_group = get_age_group(r[6])
                        if age_filter and age_group != age_filter:
                            continue
                        players.append({
                            "id": r[0], "player_name": r[1], "total_points": pts,
                            "total_games": int(r[3]), "avg_score": float(r[4]),
                            "last_played": str(r[5]), "tier": tier, "progress": progress,
                            "age_group": age_group, "country": r[7],
                        })
                    return Response({"players": players, "tiers": RANKING_TIERS})

                # Default leaderboard view
                offset = int(request.query_params.get("offset", 0))
                limit  = 20
                conditions, params = ["p.is_admin = 0"], []
                if game:
                    conditions.append("l.game = %s"); params.append(game)
                if period == "daily":
                    conditions.append("l.created_at >= CURDATE()")
                elif period == "weekly":
                    conditions.append("l.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
                elif period == "monthly":
                    conditions.append("l.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")

                where    = "WHERE " + " AND ".join(conditions)
                game_col = "" if game else ", MAX(l.game) as game"
                cur.execute(
                    f"SELECT l.player_name, l.user_id, SUM(l.score) as total_score, MAX(l.created_at) as last_played {game_col}, p.birthdate, p.country, COUNT(l.id) as total_games "
                    f"FROM leaderboard l LEFT JOIN players p ON l.user_id = p.id "
                    f"{where} GROUP BY l.player_name, l.user_id, p.birthdate, p.country ORDER BY total_score DESC LIMIT %s OFFSET %s",
                    params + [limit, offset]
                )
                rows = cur.fetchall()
                from datetime import date as date_cls
                def calc_age_group(birthdate):
                    if not birthdate: return None
                    today = date_cls.today()
                    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                    return "kids" if age <= 12 else "teen" if age <= 17 else "adult"
                players = [{
                    "player_name": r[0], "user_id": r[1], "total_score": r[2], "last_played": str(r[3]),
                    "game": r[4] if not game else None,
                    "age_group": calc_age_group(r[5] if not game else r[4]),
                    "country": r[6] if not game else r[5],
                    "total_games": int(r[7] if not game else r[6]),
                } for r in rows]

                cur.execute(
                    "SELECT DISTINCT l.game FROM leaderboard l JOIN players p ON l.user_id = p.id "
                    "WHERE p.is_admin = 0 ORDER BY l.game"
                )
                game_types = [r[0] for r in cur.fetchall()]

                return Response({"players": players, "game_types": game_types, "has_more": len(rows) == limit})

        except Exception as e:
            return Response({"error": str(e)}, status=500)
