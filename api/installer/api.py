"""
Admin/partner API for the auto-generated installer pipeline. Product
CRUD scoping (staff see everything, a partner sees only their own,
?mine=1 scopes a staff+partner account to their own partner too) mirrors
catalog.admin_api exactly — reusing _effective_partner_id rather than
re-deriving the same rule a second time.
"""
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.admin_api import _effective_partner_id
from catalog.models import Product
from catalog.models.product import ProductType
from catalog.permissions import IsStaffOrPartner
from installer.builder import build_plugin_installer
from installer.models import PluginBuild, PluginResourceFile
from installer.paths import DESTINATION_TOKENS, InvalidDestinationPath, parse_destination_path


def _product_queryset(request):
    qs = Product.objects.all()
    partner_id = _effective_partner_id(request)
    if partner_id is not None:
        qs = qs.filter(partner_id=partner_id)
    return qs


def _build_queryset(request):
    qs = PluginBuild.objects.select_related("product").prefetch_related("resource_files")
    partner_id = _effective_partner_id(request)
    if partner_id is not None:
        qs = qs.filter(product__partner_id=partner_id)
    return qs


class PluginResourceFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PluginResourceFile
        fields = ["id", "kind", "original_filename", "destination_path", "sort_order"]


class PluginBuildSerializer(serializers.ModelSerializer):
    resource_files = PluginResourceFileSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PluginBuild
        fields = [
            "id", "product", "product_name", "revit_year", "plugin_version",
            "dll_filename", "addin_filename", "status", "scope", "built_at",
            "build_log", "resource_files", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "product", "product_name", "dll_filename", "addin_filename", "status",
            "scope", "built_at", "build_log", "resource_files", "created_at", "updated_at",
        ]


class PluginBuildListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/admin/products/<product_id>/plugin-builds — one row per
    Revit year a partner is targeting for this product."""

    permission_classes = [IsStaffOrPartner]
    serializer_class = PluginBuildSerializer

    def get_queryset(self):
        product = get_object_or_404(_product_queryset(self.request), pk=self.kwargs["product_id"])
        return PluginBuild.objects.filter(product=product).prefetch_related("resource_files")

    def perform_create(self, serializer):
        product = get_object_or_404(_product_queryset(self.request), pk=self.kwargs["product_id"])
        if product.type != ProductType.PLUGIN:
            raise ValidationError({"product": "Installer builds are only available for Revit Plugin products."})
        revit_year = (self.request.data.get("revit_year") or "").strip()
        if not revit_year:
            raise ValidationError({"revit_year": "A Revit year is required."})
        if PluginBuild.objects.filter(product=product, revit_year=revit_year).exists():
            raise ValidationError({"revit_year": "A build for this Revit year already exists."})
        serializer.save(product=product, revit_year=revit_year)


class PluginBuildDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET current status/log; PATCH plugin_version; DELETE removes the build
    (and any staged files it references) entirely."""

    permission_classes = [IsStaffOrPartner]
    serializer_class = PluginBuildSerializer

    def get_queryset(self):
        return _build_queryset(self.request)


class PluginBuildDllUploadView(APIView):
    permission_classes = [IsStaffOrPartner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        build = get_object_or_404(_build_queryset(request), pk=pk)
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A .dll file is required."})
        if not uploaded.name.lower().endswith(".dll"):
            raise ValidationError({"file": "Expected a .dll file."})
        key = default_storage.save(f"plugin_builds/{build.product_id}/{build.revit_year}/dll/{uploaded.name}", uploaded)
        build.dll_storage_key = key
        build.dll_filename = uploaded.name
        build.status = PluginBuild.Status.DRAFT
        build.save(update_fields=["dll_storage_key", "dll_filename", "status", "updated_at"])
        return Response(PluginBuildSerializer(build).data)


class PluginBuildAddinUploadView(APIView):
    permission_classes = [IsStaffOrPartner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        build = get_object_or_404(_build_queryset(request), pk=pk)
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A .addin file is required."})
        if not uploaded.name.lower().endswith(".addin"):
            raise ValidationError({"file": "Expected a .addin file."})
        key = default_storage.save(
            f"plugin_builds/{build.product_id}/{build.revit_year}/addin/{uploaded.name}", uploaded
        )
        build.addin_storage_key = key
        build.addin_filename = uploaded.name
        build.status = PluginBuild.Status.DRAFT
        build.save(update_fields=["addin_storage_key", "addin_filename", "status", "updated_at"])
        return Response(PluginBuildSerializer(build).data)


class PluginResourceListCreateView(APIView):
    """POST /api/admin/plugin-builds/<id>/resources — attach a resource or
    dependency file with a destination path. The path is validated
    server-side (see installer.paths) since it's later used as a literal
    filesystem path on every customer's machine."""

    permission_classes = [IsStaffOrPartner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        build = get_object_or_404(_build_queryset(request), pk=pk)
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A file is required."})
        destination_path = (request.data.get("destination_path") or "").strip()
        try:
            parse_destination_path(destination_path)
        except InvalidDestinationPath as exc:
            raise ValidationError({"destination_path": str(exc)}) from exc
        kind = request.data.get("kind") or PluginResourceFile.Kind.RESOURCE
        if kind not in PluginResourceFile.Kind.values:
            raise ValidationError({"kind": "Must be 'resource' or 'dependency'."})

        key = default_storage.save(
            f"plugin_builds/{build.product_id}/{build.revit_year}/resources/{uploaded.name}", uploaded
        )
        resource = PluginResourceFile.objects.create(
            build=build,
            kind=kind,
            storage_key=key,
            original_filename=uploaded.name,
            destination_path=destination_path,
            sort_order=build.resource_files.count(),
        )
        build.status = PluginBuild.Status.DRAFT
        build.save(update_fields=["status", "updated_at"])
        return Response(PluginResourceFileSerializer(resource).data, status=201)


class PluginResourceDetailView(APIView):
    permission_classes = [IsStaffOrPartner]

    def delete(self, request, pk, resource_id):
        build = get_object_or_404(_build_queryset(request), pk=pk)
        resource = get_object_or_404(PluginResourceFile, pk=resource_id, build=build)
        if resource.storage_key and default_storage.exists(resource.storage_key):
            default_storage.delete(resource.storage_key)
        resource.delete()
        build.status = PluginBuild.Status.DRAFT
        build.save(update_fields=["status", "updated_at"])
        return Response(status=204)


class PluginBuildTriggerView(APIView):
    """POST /api/admin/plugin-builds/<id>/build — runs the WiX packaging
    pipeline synchronously (see installer.builder) and returns the outcome.
    There's no background task queue in this project; a build is short
    enough to run inline on the request within INSTALLER_BUILD_TIMEOUT_SECONDS."""

    permission_classes = [IsStaffOrPartner]

    def post(self, request, pk):
        build = get_object_or_404(_build_queryset(request), pk=pk)
        result = build_plugin_installer(build)
        return Response(PluginBuildSerializer(result).data)


class PluginBuildDownloadView(APIView):
    """GET /api/admin/plugin-builds/<id>/download — lets staff/partner grab
    the built .msi directly, without going through the customer purchase/
    entitlement flow. Needed to test a build (including an unpublished
    draft product) before it's ever purchasable."""

    permission_classes = [IsStaffOrPartner]

    def get(self, request, pk):
        from django.http import HttpResponseRedirect

        build = get_object_or_404(_build_queryset(request), pk=pk)
        if build.status != PluginBuild.Status.READY or not build.built_msi_storage_key:
            raise ValidationError({"detail": "This build hasn't produced an installer yet."})
        return HttpResponseRedirect(default_storage.url(build.built_msi_storage_key))


class PluginBuildDestinationOptionsView(APIView):
    """GET /api/admin/plugin-builds/destination-options — the two valid
    destination-path roots + their real on-disk hint text, so the frontend
    never hardcodes this copy separately from the backend that enforces it."""

    permission_classes = [IsStaffOrPartner]

    def get(self, request):
        return Response(
            [{"token": token, **meta} for token, meta in DESTINATION_TOKENS.items()]
        )
