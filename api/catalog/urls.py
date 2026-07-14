"""Storefront catalog API routes (mounted under /api/ in config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.views import CategoryViewSet, CollectionViewSet, ProductViewSet, home_api

# trailing_slash=False: reads (getProducts/getCategories/getProduct in lib/api.ts)
# go straight to Django server-side and never cared either way, but the reviews
# write action is called from the browser through the Next dev proxy, which
# strips a trailing slash before forwarding — DRF's default trailing-slash
# routes then hit APPEND_SLASH's can't-redirect-a-POST crash. Same fix as
# catalog/admin_urls.py, applied here because this router now has a write action.
router = DefaultRouter(trailing_slash=False)
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("collections", CollectionViewSet, basename="collection")

urlpatterns = [
    path("home", home_api, name="home-api"),
    path("", include(router.urls)),
]
