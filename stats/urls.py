from django.urls import path
from .views import StatsView

urlpatterns = [
    path("", StatsView.as_view(), name="stats"),
]
