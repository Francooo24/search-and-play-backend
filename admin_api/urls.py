from django.urls import path
from .views import (
    AdminPlayersView, AdminBanView, AdminUnbanView,
    AdminDeleteView, AdminRestoreView, AdminEditView,
    AdminStatsView, AdminLeaderboardView, AdminGameStatsView,
)

urlpatterns = [
    path("players/",     AdminPlayersView.as_view(),     name="admin_players"),
    path("ban/",         AdminBanView.as_view(),          name="admin_ban"),
    path("unban/",       AdminUnbanView.as_view(),        name="admin_unban"),
    path("delete/",      AdminDeleteView.as_view(),       name="admin_delete"),
    path("restore/",     AdminRestoreView.as_view(),      name="admin_restore"),
    path("edit/",        AdminEditView.as_view(),         name="admin_edit"),
    path("stats/",       AdminStatsView.as_view(),        name="admin_stats"),
    path("leaderboard/", AdminLeaderboardView.as_view(),  name="admin_leaderboard"),
    path("gamestats/",   AdminGameStatsView.as_view(),    name="admin_gamestats"),
]
