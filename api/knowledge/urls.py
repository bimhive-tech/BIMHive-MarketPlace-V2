"""Knowledge Base + legal page routes (mounted under /api/ in config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from knowledge.views import ArticleViewSet

# trailing_slash=False to match catalog/urls.py (the Next proxy strips slashes).
router = DefaultRouter(trailing_slash=False)
router.register("articles", ArticleViewSet, basename="article")

urlpatterns = [path("", include(router.urls))]
