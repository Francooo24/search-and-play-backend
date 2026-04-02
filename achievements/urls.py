from django.urls import path
from .views import AchievementsView, CheckAchievementsView

urlpatterns = [
    path("",       AchievementsView.as_view(),      name="achievements"),
    path("check/", CheckAchievementsView.as_view(),  name="achievements_check"),
]
