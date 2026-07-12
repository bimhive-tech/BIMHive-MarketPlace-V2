"""
One-time import of licensing compatibility data from the legacy installer-generator DB.

Field-installed plugins activate against specific product `code` strings and existing
machine licenses that live in the legacy DB — NOT in this marketplace DB. Run this once
(with the legacy source URL) so V2 keeps those installs working. V2's LICENSE_PEPPER must
also equal production's, or every stored fingerprint hash will mismatch.

    python manage.py import_legacy_license_data --source-url postgresql://...

Reads legacy tables `products`, `machine_licenses`, `license_events` and upserts them into
V2's LicensedProduct / MachineLicense / LicenseEvent (matched by primary key).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from licensing.models import LicensedProduct, LicenseEvent, MachineLicense


class Command(BaseCommand):
    help = "Import products, machine licenses, and license events from the legacy licensing DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-url",
            required=True,
            help="Legacy PostgreSQL connection string (installer-generator DB).",
        )

    def handle(self, *args, **options):
        source_url = (options["source_url"] or "").strip()
        if not source_url:
            raise CommandError("A non-empty --source-url is required.")

        try:
            import psycopg  # noqa: local import so the command is optional at runtime
        except ImportError as exc:  # pragma: no cover
            raise CommandError("psycopg is required to run the legacy import.") from exc

        with psycopg.connect(source_url) as conn:
            with conn.cursor() as cur, transaction.atomic():
                self._import_products(cur)
                self._import_machine_licenses(cur)
                self._import_events(cur)

        self.stdout.write(self.style.SUCCESS("Legacy license data imported into V2."))

    def _import_products(self, cur):
        cur.execute(
            "select id, code, name, revit_year, default_trial_days, is_active, created_at "
            "from products order by created_at, code"
        )
        for pid, code, name, revit_year, trial_days, is_active, created_at in cur.fetchall():
            LicensedProduct.objects.update_or_create(
                id=pid,
                defaults={
                    "code": code,
                    "slug": slugify(code),
                    "name": name,
                    "revit_year": revit_year or "",
                    "default_trial_days": trial_days or 30,
                    "is_active": bool(is_active),
                    "created_at": created_at,
                },
            )

    def _import_machine_licenses(self, cur):
        cur.execute(
            "select id, product_id, machine_fingerprint_hash, fingerprint_version, status, "
            "started_at, expires_at, first_seen_at, last_seen_at, install_count, plugin_version, "
            "machine_data, metadata from machine_licenses"
        )
        for row in cur.fetchall():
            (
                lid, product_id, machine_hash, fp_version, status, started_at, expires_at,
                first_seen_at, last_seen_at, install_count, plugin_version, machine_data, metadata,
            ) = row
            MachineLicense.objects.update_or_create(
                id=lid,
                defaults={
                    "product_id": product_id,
                    "machine_fingerprint_hash": machine_hash,
                    "fingerprint_version": fp_version,
                    "status": status,
                    "started_at": started_at,
                    "expires_at": expires_at,
                    "first_seen_at": first_seen_at,
                    "last_seen_at": last_seen_at,
                    "install_count": install_count,
                    "plugin_version": plugin_version or "",
                    "machine_data": machine_data or {},
                    "metadata": metadata or {},
                },
            )

    def _import_events(self, cur):
        cur.execute(
            "select id, product_id, machine_license_id, machine_fingerprint_hash, event_type, "
            "event_time, payload from license_events"
        )
        for eid, product_id, ml_id, machine_hash, event_type, event_time, payload in cur.fetchall():
            LicenseEvent.objects.update_or_create(
                id=eid,
                defaults={
                    "product_id": product_id,
                    "machine_license_id": ml_id,
                    "machine_fingerprint_hash": machine_hash,
                    "event_type": event_type,
                    "event_time": event_time,
                    "payload": payload or {},
                },
            )
