from django.urls import path
from .views import ScoreView, FavoriteGamesView, FavoriteWordsView, ActivityView, SearchLogView, DailyChallengeView

urlpatterns = [
    path("score/",           ScoreView.as_view(),          name="game_score"),
    path("favorites/games/", FavoriteGamesView.as_view(),  name="favorite_games"),
    path("favorites/words/", FavoriteWordsView.as_view(),  name="favorite_words"),
    path("activity/",        ActivityView.as_view(),        name="activity"),
    path("search/",          SearchLogView.as_view(),       name="search_log"),
    path("daily-challenge/", DailyChallengeView.as_view(), name="daily_challenge"),
]
