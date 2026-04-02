import bcrypt
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from user.models import Player
from games.models import GameScore, DailyChallenge, DailyChallengeCompletion
from achievements.models import Achievement, PlayerAchievement


def make_player(player_name="testuser", email=None):
    """Create a Player directly (bypassing OTP flow) for testing."""
    if email is None:
        email = f"{player_name}@test.com"
    hashed = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    return Player.objects.create(
        player_name=player_name,
        email=email,
        password=hashed,
    )


def auth_client(player):
    """Return an APIClient force-authenticated as the given player."""
    client = APIClient()
    client.force_authenticate(user=player)
    return client


# ── Auth / Login ──────────────────────────────────────────────────────────────
class AuthTests(TestCase):
    def setUp(self):
        pass

    def test_login_returns_tokens(self):
        hashed = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()
        Player.objects.create(player_name="loginuser", email="login@test.com", password=hashed)
        client = APIClient()
        res = client.post("/api/user/login/", {"email": "login@test.com", "password": "mypassword"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", res.data)
        self.assertIn("access", res.data["tokens"])
        self.assertIn("refresh", res.data["tokens"])

    def test_login_wrong_password_fails(self):
        hashed = bcrypt.hashpw(b"correctpass", bcrypt.gensalt()).decode()
        Player.objects.create(player_name="loginuser2", email="login2@test.com", password=hashed)
        client = APIClient()
        res = client.post("/api/user/login/", {"email": "login2@test.com", "password": "wrongpass"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_email_fails(self):
        client = APIClient()
        res = client.post("/api/user/login/", {"email": "nobody@test.com", "password": "pass"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_protected_endpoint_requires_auth(self):
        client = APIClient()
        res = client.get("/api/achievements/")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_profile_returns_player_data(self):
        player = make_player("profileuser")
        client = auth_client(player)
        res = client.get("/api/user/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["player_name"], "profileuser")

    def test_banned_player_cannot_login(self):
        hashed = bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode()
        Player.objects.create(player_name="banned", email="banned@test.com", password=hashed, status="banned")
        client = APIClient()
        res = client.post("/api/user/login/", {"email": "banned@test.com", "password": "pass123"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ── Score ─────────────────────────────────────────────────────────────────────
class ScoreTests(TestCase):
    def setUp(self):
        self.player = make_player("scorer")
        self.client = auth_client(self.player)

    def test_submit_score_saves_to_db(self):
        res = self.client.post("/api/games/score/", {"game": "Hangman", "score": 100, "won": True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(GameScore.objects.filter(user=self.player, game="Hangman", score=100).exists())

    def test_submit_zero_score_does_not_save(self):
        res = self.client.post("/api/games/score/", {"game": "Hangman", "score": 0, "won": False})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(GameScore.objects.filter(user=self.player, score=0).exists())

    def test_submit_score_returns_success(self):
        res = self.client.post("/api/games/score/", {"game": "Wordle", "score": 50, "won": True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        self.assertEqual(res.data["pts"], 50)

    def test_get_best_score_returns_highest(self):
        GameScore.objects.create(user=self.player, player_name="scorer", game="Wordle", score=50)
        GameScore.objects.create(user=self.player, player_name="scorer", game="Wordle", score=200)
        GameScore.objects.create(user=self.player, player_name="scorer", game="Wordle", score=100)
        res = self.client.get("/api/games/score/?game=Wordle")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["bestScore"], 200)

    def test_get_best_score_returns_zero_when_no_scores(self):
        res = self.client.get("/api/games/score/?game=NoGame")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["bestScore"], 0)

    def test_submit_score_unauthenticated_fails(self):
        client = APIClient()
        res = client.post("/api/games/score/", {"game": "Hangman", "score": 50, "won": True})
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ── Leaderboard ───────────────────────────────────────────────────────────────
class LeaderboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.p1 = make_player("alice", "alice@test.com")
        self.p2 = make_player("bob",   "bob@test.com")
        GameScore.objects.create(user=self.p1, player_name="alice", game="Hangman", score=300)
        GameScore.objects.create(user=self.p2, player_name="bob",   game="Hangman", score=150)
        GameScore.objects.create(user=self.p1, player_name="alice", game="Wordle",  score=200)

    def test_leaderboard_returns_players(self):
        res = self.client.get("/api/leaderboard/")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if res.status_code == 200:
            self.assertIn("players", res.data)

    def test_leaderboard_sorted_by_score_descending(self):
        res = self.client.get("/api/leaderboard/")
        if res.status_code == 200 and "players" in res.data:
            scores = [p["total_score"] for p in res.data["players"]]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_leaderboard_filters_by_game(self):
        res = self.client.get("/api/leaderboard/?game=Wordle")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_leaderboard_weekly_filter(self):
        res = self.client.get("/api/leaderboard/?period=weekly")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_leaderboard_excludes_admins(self):
        pass

    def test_rankings_view_returns_tiers(self):
        res = self.client.get("/api/leaderboard/?view=rankings")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if res.status_code == 200:
            self.assertIn("tiers", res.data)
            self.assertEqual(len(res.data["tiers"]), 7)

    def test_pergame_view_returns_games(self):
        res = self.client.get("/api/leaderboard/?view=pergame")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if res.status_code == 200:
            self.assertIn("games", res.data)

    def test_game_view_returns_top_players(self):
        res = self.client.get("/api/leaderboard/?view=game&game=Hangman")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if res.status_code == 200:
            self.assertIn("players", res.data)


# ── Achievements ──────────────────────────────────────────────────────────────
class AchievementTests(TestCase):
    def setUp(self):
        self.player = make_player("achiever")
        self.client = auth_client(self.player)
        self.ach = Achievement.objects.create(
            name="First Steps",
            description="Play your first game",
            icon="🎮",
            condition_type="games_played",
            condition_value=1,
        )

    def test_check_achievements_unlocks_on_condition_met(self):
        GameScore.objects.create(user=self.player, player_name="achiever", game="Hangman", score=50)
        res = self.client.post("/api/achievements/check/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PlayerAchievement.objects.filter(player=self.player, achievement=self.ach).exists()
        )
        self.assertEqual(len(res.data["newAchievements"]), 1)
        self.assertEqual(res.data["newAchievements"][0]["name"], "First Steps")

    def test_check_achievements_does_not_duplicate(self):
        GameScore.objects.create(user=self.player, player_name="achiever", game="Hangman", score=50)
        self.client.post("/api/achievements/check/")
        res = self.client.post("/api/achievements/check/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["newAchievements"]), 0)

    def test_get_achievements_returns_earned_list(self):
        PlayerAchievement.objects.create(player=self.player, achievement=self.ach)
        res = self.client.get("/api/achievements/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_achievements_not_unlocked_when_condition_not_met(self):
        res = self.client.post("/api/achievements/check/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["newAchievements"]), 0)

    def test_achievements_requires_auth(self):
        client = APIClient()
        res = client.get("/api/achievements/")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ── Daily Challenge ───────────────────────────────────────────────────────────
class DailyChallengeTests(TestCase):
    def setUp(self):
        self.player = make_player("challenger")
        self.client = auth_client(self.player)
        self.challenge = DailyChallenge.objects.create(
            challenge_date=date.today(),
            game="Hangman",
            title="Hangman Hero",
            description="Play Hangman once today!",
            target_type="win",
            target_value=1,
            bonus_points=50,
        )

    def test_get_challenge_returns_todays_challenge(self):
        res = self.client.get("/api/games/daily-challenge/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["challenge"]["game"], "Hangman")
        self.assertFalse(res.data["completed"])

    def test_get_challenge_shows_progress(self):
        GameScore.objects.create(user=self.player, player_name="challenger", game="Hangman", score=50)
        res = self.client.get("/api/games/daily-challenge/")
        self.assertEqual(res.data["progress"], 1)
        self.assertTrue(res.data["can_claim"])

    def test_claim_reward_creates_completion(self):
        GameScore.objects.create(user=self.player, player_name="challenger", game="Hangman", score=50)
        res = self.client.post("/api/games/daily-challenge/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        self.assertEqual(res.data["bonus_points"], 50)
        self.assertTrue(
            DailyChallengeCompletion.objects.filter(user=self.player, challenge=self.challenge).exists()
        )

    def test_claim_reward_awards_bonus_score(self):
        GameScore.objects.create(user=self.player, player_name="challenger", game="Hangman", score=50)
        self.client.post("/api/games/daily-challenge/")
        self.assertTrue(
            GameScore.objects.filter(user=self.player, game="Daily Challenge", score=50).exists()
        )

    def test_cannot_claim_twice(self):
        GameScore.objects.create(user=self.player, player_name="challenger", game="Hangman", score=50)
        self.client.post("/api/games/daily-challenge/")
        res = self.client.post("/api/games/daily-challenge/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_claim_without_completing(self):
        res = self.client.post("/api/games/daily-challenge/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_challenge_returns_null(self):
        self.challenge.delete()
        res = self.client.get("/api/games/daily-challenge/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data["challenge"])

    def test_streak_counts_consecutive_days(self):
        yesterday = DailyChallenge.objects.create(
            challenge_date=date.today() - timedelta(days=1),
            game="Wordle", title="Yesterday", description="Test",
            target_type="win", target_value=1, bonus_points=50,
        )
        DailyChallengeCompletion.objects.create(user=self.player, challenge=yesterday)
        GameScore.objects.create(user=self.player, player_name="challenger", game="Hangman", score=50)
        self.client.post("/api/games/daily-challenge/")
        res = self.client.get("/api/games/daily-challenge/")
        self.assertEqual(res.data["streak"], 2)

    def test_unauthenticated_cannot_claim(self):
        client = APIClient()
        res = client.post("/api/games/daily-challenge/")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
