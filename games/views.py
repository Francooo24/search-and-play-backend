from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from datetime import date

from user.models import Player
from .models import GameScore, FavoriteGame, FavoriteWord, ActivityLog, DailyChallenge, DailyChallengeCompletion
from .serializers import SubmitScoreSerializer


def _get_player(request):
    if isinstance(request.user, Player):
        return request.user
    if request.auth and hasattr(request.auth, 'get'):
        try:
            return Player.objects.get(id=request.auth.get("user_id"))
        except Player.DoesNotExist:
            return None
    return None


class ScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        player = _get_player(request)
        if not player:
            return Response({"bestScore": 0})
        game = request.query_params.get("game", "").strip()
        if not game:
            return Response({"bestScore": 0})
        best = (
            GameScore.objects.filter(user=player, game=game)
            .order_by("-score")
            .values_list("score", flat=True)
            .first()
        )
        return Response({"bestScore": best or 0})

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"error": "Player not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubmitScoreSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        pts  = data["score"]
        game = data["game"].strip()

        if pts > 0:
            GameScore.objects.create(
                user=player, player_name=player.player_name, game=game, score=pts
            )

        result = f"won with {pts} pts" if data.get("won") else "lost"
        ActivityLog.objects.create(
            player_name=player.player_name,
            activity=f'Played "{game}" — {result}',
        )

        return Response({"success": True, "pts": pts})


class FavoriteGamesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"success": False}, status=status.HTTP_401_UNAUTHORIZED)

        action = request.data.get("action")
        game   = (request.data.get("game") or "").strip()

        if not game or action not in ("save", "remove"):
            return Response({"success": False}, status=status.HTTP_400_BAD_REQUEST)

        if action == "save":
            FavoriteGame.objects.get_or_create(user=player, game=game)
            return Response({"success": True, "saved": True})
        else:
            FavoriteGame.objects.filter(user=player, game=game).delete()
            return Response({"success": True, "saved": False})


class FavoriteWordsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"success": False}, status=status.HTTP_401_UNAUTHORIZED)

        action = request.data.get("action")
        word   = (request.data.get("word") or "").strip()

        if not word or action not in ("save", "remove"):
            return Response({"success": False}, status=status.HTTP_400_BAD_REQUEST)

        if action == "save":
            FavoriteWord.objects.get_or_create(user=player, word=word)
            return Response({"success": True, "saved": True})
        else:
            FavoriteWord.objects.filter(user=player, word=word).delete()
            return Response({"success": True, "saved": False})


class ActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        activity = (request.data.get("activity") or "").strip()
        if not activity:
            return Response({"error": "Missing activity"}, status=status.HTTP_400_BAD_REQUEST)

        ActivityLog.objects.create(player_name=player.player_name, activity=activity)
        return Response({"success": True})


class SearchLogView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = _get_player(request)
        if not player:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)

        word = (request.data.get("word") or "").strip()
        if not word:
            return Response({"ok": False, "error": "Invalid word"}, status=status.HTTP_400_BAD_REQUEST)

        ActivityLog.objects.create(
            player_name=player.player_name,
            activity=f'Searched for "{word}"',
        )
        return Response({"ok": True})


class DailyChallengeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        player = _get_player(request)
        today  = date.today()

        challenge = DailyChallenge.objects.filter(challenge_date=today).first()
        if not challenge:
            return Response({"challenge": None})

        completed = False
        progress  = 0
        can_claim = False
        streak    = 0

        if player:
            completed = DailyChallengeCompletion.objects.filter(user=player, challenge=challenge).exists()
            if not completed and challenge.target_type == "win":
                progress = GameScore.objects.filter(
                    user=player, game=challenge.game, created_at__date=today
                ).count()
                can_claim = progress >= challenge.target_value

            # streak: consecutive days completed
            from datetime import timedelta
            check = today
            while True:
                has = DailyChallengeCompletion.objects.filter(
                    user=player, challenge__challenge_date=check
                ).exists()
                if has:
                    streak += 1
                    check -= timedelta(days=1)
                else:
                    break

        # history: last 7 completions
        history = []
        if player:
            for c in DailyChallengeCompletion.objects.filter(user=player).select_related("challenge").order_by("-completed_at")[:7]:
                history.append({
                    "challenge_date": str(c.challenge.challenge_date),
                    "game":           c.challenge.game,
                    "title":          c.challenge.title,
                    "bonus_points":   c.challenge.bonus_points,
                    "completed_at":   c.completed_at.isoformat(),
                })

        return Response({
            "challenge": {
                "id":           challenge.id,
                "game":         challenge.game,
                "title":        challenge.title,
                "description":  challenge.description,
                "target_value": challenge.target_value,
                "bonus_points": challenge.bonus_points,
            },
            "completed": completed,
            "progress":  progress,
            "can_claim": can_claim,
            "streak":    streak,
            "history":   history,
        })

    def post(self, request):
        """Claim today's daily challenge reward."""
        player = _get_player(request)
        if not player:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        today = date.today()
        try:
            challenge = DailyChallenge.objects.get(challenge_date=today)
        except DailyChallenge.DoesNotExist:
            return Response({"error": "No challenge today"}, status=status.HTTP_404_NOT_FOUND)

        if DailyChallengeCompletion.objects.filter(user=player, challenge=challenge).exists():
            return Response({"error": "Already claimed"}, status=status.HTTP_400_BAD_REQUEST)

        progress = GameScore.objects.filter(
            user=player, game=challenge.game, created_at__date=today
        ).count()
        if progress < challenge.target_value:
            return Response({"error": "Challenge not completed yet"}, status=status.HTTP_400_BAD_REQUEST)

        DailyChallengeCompletion.objects.get_or_create(user=player, challenge=challenge)
        GameScore.objects.create(
            user=player,
            player_name=player.player_name,
            game="Daily Challenge",
            score=challenge.bonus_points,
        )
        return Response({"success": True, "bonus_points": challenge.bonus_points})
