from django.urls import path

from installer.api import (
    PluginBuildAddinUploadView,
    PluginBuildDestinationOptionsView,
    PluginBuildDetailView,
    PluginBuildDllUploadView,
    PluginBuildDownloadView,
    PluginBuildListCreateView,
    PluginBuildTriggerView,
    PluginResourceDetailView,
    PluginResourceListCreateView,
)

urlpatterns = [
    path("plugin-builds/destination-options", PluginBuildDestinationOptionsView.as_view(), name="plugin-build-destination-options"),
    path("products/<int:product_id>/plugin-builds", PluginBuildListCreateView.as_view(), name="plugin-build-list-create"),
    path("plugin-builds/<uuid:pk>", PluginBuildDetailView.as_view(), name="plugin-build-detail"),
    path("plugin-builds/<uuid:pk>/dll", PluginBuildDllUploadView.as_view(), name="plugin-build-dll"),
    path("plugin-builds/<uuid:pk>/addin", PluginBuildAddinUploadView.as_view(), name="plugin-build-addin"),
    path("plugin-builds/<uuid:pk>/resources", PluginResourceListCreateView.as_view(), name="plugin-build-resources"),
    path(
        "plugin-builds/<uuid:pk>/resources/<uuid:resource_id>",
        PluginResourceDetailView.as_view(),
        name="plugin-build-resource-detail",
    ),
    path("plugin-builds/<uuid:pk>/build", PluginBuildTriggerView.as_view(), name="plugin-build-trigger"),
    path("plugin-builds/<uuid:pk>/download", PluginBuildDownloadView.as_view(), name="plugin-build-download"),
]
