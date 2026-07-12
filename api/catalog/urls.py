"""Storefront catalog API routes (mounted under /api/ in config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.views import CategoryViewSet, CollectionViewSet, ProductViewSet, home_api

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("collections", CollectionViewSet, basename="collection")

urlpatterns = [
    path("home", home_api, name="home-api"),
    path("", include(router.urls)),
]
