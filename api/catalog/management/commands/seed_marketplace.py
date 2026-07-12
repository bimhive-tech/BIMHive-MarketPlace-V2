"""
Seed the marketplace with a realistic sample catalog (no lorem, no fake magic values).
Content mirrors the design mockups so the storefront renders true-to-design locally.

Idempotent: safe to run repeatedly (uses get_or_create / update_or_create).

    python manage.py seed_marketplace
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import (
    Category,
    ChangelogEntry,
    Collection,
    CompatibilityEntry,
    Documentation,
    DocSection,
    KeyFeature,
    Partner,
    Product,
    Tag,
)
from catalog.models.product import ProductStatus, ProductType
from licensing.models import LicensedProduct
from reviews.models import Review, refresh_product_rating

CATEGORIES = [
    ("Revit Plugins", "puzzle"),
    ("Automation Tools", "bolt"),
    ("Dynamo Scripts", "workflow"),
    ("BIM Libraries", "library"),
    ("Templates", "template"),
    ("Training & Courses", "graduation-cap"),
    ("Integrations", "plug"),
    ("Other Tools", "wrench"),
]

PARTNERS = [
    ("BIMHIVE", "First-party tools by the BIM Hive team", True),
    ("Arch-Tools", "Automation utilities for architecture teams", True),
    ("DynamoLab", "Advanced Dynamo packages and nodes", True),
    ("DataBuild", "BIM data and analytics specialists", True),
    ("BIM Solutions", "Enterprise BIM content and libraries", True),
]

COLLECTIONS = [
    ("Revit Essentials", "star", "The must-have plugins every Revit user needs."),
    ("Automation Suite", "workflow", "Automate repetitive modelling and documentation."),
    ("BIM Management", "library", "Tools for managing models, data, and standards."),
    ("Data & Analytics", "chart", "Turn your BIM models into actionable insight."),
]

# Each product: name, type, category, partner, price, team_price, short, desc, version,
# released, rating_avg, rating_count, downloads, revit_years, tags, features, changelog,
# compatibility, collection names.
PRODUCTS = [
    {
        "name": "BIM OneClick",
        "type": ProductType.PLUGIN,
        "category": "Revit Plugins",
        "partner": "BIMHIVE",
        "price": Decimal("49.00"),
        "team_price": Decimal("199.00"),
        "short": "Productivity plugin for Revit",
        "description": (
            "BIM OneClick streamlines your Revit workflow by automating essential tasks that "
            "every BIM professional deals with daily. Save time, reduce errors, and focus on "
            "what matters most—design."
        ),
        "version": "2.1.0",
        "released": date(2023, 1, 10),
        "rating": [85, 10, 3, 1, 1],  # % per 5..1 star, from the mockup
        "rating_count": 120,
        "downloads": 1250,
        "featured": True,
        "revit_years": ["2020", "2021", "2022", "2023", "2024", "2025"],
        "tags": ["Productivity", "Automation", "Documentation", "Model Management"],
        "features": [
            ("Model Cleanup", "Remove unused items, purge, and audit your model to keep it light and efficient.", "broom"),
            ("View Management", "Create, organize, and standardize views with custom templates and filters.", "eye"),
            ("Documentation", "Automate sheet creation, naming, parameter checks, and exports.", "document"),
        ],
        "changelog": [
            ("2.1.0", date(2024, 5, 14), "Improved performance for larger models\nNew sheet naming presets\nAdded support for Revit 2025\nBug fixes and stability improvements"),
            ("2.0.0", date(2023, 11, 2), "Redesigned interface\nBatch view creation\nParameter check engine"),
        ],
        "compatibility": [("Revit", "2020–2025"), ("Platform", "Windows"), ("Language", "English")],
        "collections": ["Revit Essentials", "Automation Suite"],
        "doc": {
            "title": "BIM OneClick Documentation",
            "summary": "Install, configure, and get the most out of BIM OneClick.",
            "overview": "This guide covers installation, the OneClick ribbon, and each automation module.",
            "sections": [
                ("Installation", "Download the installer for your Revit version and run it while Revit is closed. The BIM OneClick tab appears on the ribbon on next launch."),
                ("Running Model Cleanup", "Open the Model Cleanup panel, choose the categories to audit, and click Run. Review the report before applying changes."),
            ],
        },
    },
    {
        "name": "Sheet Manager Pro",
        "type": ProductType.PLUGIN,
        "category": "Automation Tools",
        "partner": "Arch-Tools",
        "price": Decimal("59.00"),
        "team_price": Decimal("239.00"),
        "short": "Automate sheet creation and organization",
        "description": (
            "Sheet Manager Pro takes the tedium out of sheet set-up. Batch-create, rename, and "
            "renumber sheets from a spreadsheet, and keep your titleblocks consistent across the project."
        ),
        "version": "1.6.2",
        "released": date(2023, 3, 22),
        "rating": [80, 12, 5, 2, 1],
        "rating_count": 85,
        "downloads": 890,
        "featured": True,
        "revit_years": ["2022", "2023", "2024", "2025"],
        "tags": ["Automation", "Documentation", "Sheets"],
        "features": [
            ("Batch Sheet Creation", "Create hundreds of sheets from a spreadsheet in one step.", "layers"),
            ("Smart Renumbering", "Renumber and reorder sheets without breaking references.", "hash"),
            ("Titleblock Sync", "Keep titleblock data consistent across every sheet.", "grid"),
        ],
        "changelog": [
            ("1.6.2", date(2024, 5, 10), "Excel import improvements\nRevit 2025 support\nFixed renumber edge cases"),
        ],
        "compatibility": [("Revit", "2022–2025"), ("Platform", "Windows"), ("Language", "English")],
        "collections": ["Automation Suite"],
        "doc": None,
    },
    {
        "name": "Dynamo Toolkit",
        "type": ProductType.SCRIPT,
        "category": "Dynamo Scripts",
        "partner": "DynamoLab",
        "price": Decimal("39.00"),
        "team_price": Decimal("159.00"),
        "short": "Essential nodes for advanced automation",
        "description": (
            "A curated package of Dynamo nodes for advanced automation—geometry, data, and "
            "documentation helpers that plug straight into your graphs."
        ),
        "version": "3.0.1",
        "released": date(2022, 9, 5),
        "rating": [88, 8, 2, 1, 1],
        "rating_count": 210,
        "downloads": 2100,
        "featured": True,
        "revit_years": ["2022", "2023", "2024", "2025"],
        "tags": ["Automation", "Dynamo", "Productivity"],
        "features": [
            ("Geometry Nodes", "Robust helpers for complex geometry operations.", "workflow"),
            ("Data Nodes", "Read, transform, and write model data with ease.", "database"),
            ("Documentation Nodes", "Automate schedules, tags, and annotations.", "document"),
        ],
        "changelog": [
            ("3.0.1", date(2024, 5, 8), "New geometry nodes\nPerformance improvements\nRevit 2025 / Dynamo 3.0 support"),
        ],
        "compatibility": [("Revit", "2022–2025"), ("Dynamo", "2.x–3.0"), ("Platform", "Windows")],
        "collections": ["Automation Suite", "Data & Analytics"],
        "doc": None,
    },
    {
        "name": "BIM Data Dashboard",
        "type": ProductType.PLUGIN,
        "category": "Other Tools",
        "partner": "DataBuild",
        "price": Decimal("69.00"),
        "team_price": Decimal("279.00"),
        "short": "Real-time insights from your BIM model",
        "description": (
            "Connect your Revit model to live dashboards. Track quantities, completeness, and "
            "quality metrics as your model evolves."
        ),
        "version": "1.2.0",
        "released": date(2023, 6, 18),
        "rating": [78, 14, 5, 2, 1],
        "rating_count": 67,
        "downloads": 320,
        "featured": True,
        "revit_years": ["2023", "2024", "2025"],
        "tags": ["Analytics", "Data", "Reporting"],
        "features": [
            ("Live Metrics", "Real-time quantity and completeness tracking.", "chart"),
            ("Custom Dashboards", "Build the views your team actually needs.", "grid"),
            ("Export & Share", "Export to Excel, PDF, or share a live link.", "share"),
        ],
        "changelog": [
            ("1.2.0", date(2024, 5, 12), "New dashboard widgets\nFaster model sync\nRevit 2025 support"),
        ],
        "compatibility": [("Revit", "2023–2025"), ("Platform", "Windows"), ("Language", "English")],
        "collections": ["Data & Analytics", "BIM Management"],
        "doc": None,
    },
    {
        "name": "Auto Number",
        "type": ProductType.PLUGIN,
        "category": "Revit Plugins",
        "partner": "BIMHIVE",
        "price": Decimal("29.00"),
        "team_price": Decimal("119.00"),
        "short": "Automatic numbering for Revit elements",
        "description": (
            "Number doors, rooms, grids, and any family instances automatically, following rules "
            "you define. Consistent numbering across the whole project in seconds."
        ),
        "version": "1.4.0",
        "released": date(2023, 2, 1),
        "rating": [82, 11, 4, 2, 1],
        "rating_count": 54,
        "downloads": 640,
        "featured": False,
        "revit_years": ["2022", "2023", "2024", "2025"],
        "tags": ["Productivity", "Automation"],
        "features": [
            ("Rule-based Numbering", "Define numbering rules per category.", "hash"),
            ("Spatial Ordering", "Number by location, path, or selection order.", "workflow"),
        ],
        "changelog": [("1.4.0", date(2024, 5, 13), "Path-based ordering\nRevit 2025 support")],
        "compatibility": [("Revit", "2022–2025"), ("Platform", "Windows")],
        "collections": ["Revit Essentials"],
        "doc": None,
    },
    {
        "name": "Family Loader",
        "type": ProductType.LIBRARY,
        "category": "BIM Libraries",
        "partner": "BIM Solutions",
        "price": Decimal("19.00"),
        "team_price": Decimal("79.00"),
        "short": "Batch load families into Revit projects",
        "description": (
            "Load and manage families in bulk. Point Family Loader at a folder and it places, "
            "updates, or replaces families across your project consistently."
        ),
        "version": "1.1.0",
        "released": date(2023, 4, 12),
        "rating": [76, 15, 5, 3, 1],
        "rating_count": 41,
        "downloads": 560,
        "featured": False,
        "revit_years": ["2022", "2023", "2024", "2025"],
        "tags": ["Content", "Productivity", "Library"],
        "features": [
            ("Batch Load", "Load whole folders of families at once.", "layers"),
            ("Smart Update", "Update existing families without duplicates.", "refresh"),
        ],
        "changelog": [("1.1.0", date(2024, 5, 7), "Folder watch\nRevit 2025 support")],
        "compatibility": [("Revit", "2022–2025"), ("Platform", "Windows")],
        "collections": ["BIM Management"],
        "doc": None,
    },
]

REVIEW_SAMPLES = [
    (5, "Massive time saver", "Cut our sheet setup from hours to minutes.", "Alex Johnson"),
    (5, "Essential tool", "Can't imagine working without it now.", "Sarah Williams"),
    (4, "Very good", "Works well, would love more presets.", "Michael Brown"),
    (5, "Rock solid", "Stable on large models, great support.", "Priya N."),
]


class Command(BaseCommand):
    help = "Seed the marketplace with a realistic sample catalog."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {
            name: Category.objects.get_or_create(name=name, defaults={"icon": icon, "sort_order": i})[0]
            for i, (name, icon) in enumerate(CATEGORIES)
        }
        partners = {
            name: Partner.objects.get_or_create(
                name=name, defaults={"tagline": tagline, "is_verified": verified}
            )[0]
            for name, tagline, verified in PARTNERS
        }
        collections = {
            name: Collection.objects.get_or_create(
                name=name, defaults={"icon": icon, "description": desc, "is_featured": True, "sort_order": i}
            )[0]
            for i, (name, icon, desc) in enumerate(COLLECTIONS)
        }

        for spec in PRODUCTS:
            self._seed_product(spec, categories, partners, collections)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CATEGORIES)} categories, {len(PARTNERS)} partners, "
            f"{len(COLLECTIONS)} collections, {len(PRODUCTS)} products."
        ))

    def _seed_product(self, spec, categories, partners, collections):
        product, _ = Product.objects.update_or_create(
            slug=self._slug(spec["name"]),
            defaults={
                "name": spec["name"],
                "type": spec["type"],
                "category": categories[spec["category"]],
                "partner": partners[spec["partner"]],
                "short_description": spec["short"],
                "description": spec["description"],
                "price": spec["price"],
                "team_price": spec["team_price"],
                "currency": "USD",
                "version": spec["version"],
                "released_at": spec["released"],
                "download_count": spec["downloads"],
                "is_featured": spec["featured"],
                "status": ProductStatus.PUBLISHED,
                "default_trial_days": 30,
            },
        )

        product.tags.set(
            Tag.objects.get_or_create(name=t)[0] for t in spec["tags"]
        )

        # No fabricated imagery: real product art is uploaded to R2 via the admin.
        # Until then the frontend renders the brand's signature wireframe line-art
        # placeholder (style.md §9), which is the intended on-brand product visual.
        product.features.all().delete()
        for i, (title, desc, icon) in enumerate(spec["features"]):
            KeyFeature.objects.create(product=product, title=title, description=desc, icon=icon, sort_order=i)

        product.changelog.all().delete()
        for i, (version, released, notes) in enumerate(spec["changelog"]):
            ChangelogEntry.objects.create(product=product, version=version, released_at=released, notes=notes, sort_order=i)

        product.compatibility.all().delete()
        for i, (label, value) in enumerate(spec["compatibility"]):
            CompatibilityEntry.objects.create(product=product, label=label, value=value, sort_order=i)

        for cname in spec["collections"]:
            collections[cname].products.add(product)

        if spec.get("doc"):
            self._seed_doc(product, spec["doc"])

        self._seed_reviews(product, spec["rating"], spec["rating_count"])
        self._seed_license_skus(product, spec["revit_years"])

    def _seed_doc(self, product, doc):
        documentation, _ = Documentation.objects.update_or_create(
            product=product,
            defaults={"title": doc["title"], "summary": doc["summary"], "overview": doc["overview"], "is_published": True},
        )
        documentation.sections.all().delete()
        for i, (title, body) in enumerate(doc["sections"]):
            DocSection.objects.create(documentation=documentation, title=title, body=body, sort_order=i)

    def _seed_reviews(self, product, breakdown_pct, count):
        product.reviews.all().delete()
        # Recreate a small, representative set of visible reviews.
        for rating, title, body, name in REVIEW_SAMPLES:
            Review.objects.create(
                product=product, author_name=name, rating=rating, title=title, body=body,
                is_verified_purchase=True,
            )
        # breakdown_pct is [5★%, 4★%, 3★%, 2★%, 1★%] from the mockup. Convert to
        # per-star counts scaled to the total, then persist the aggregate as the
        # source of truth for the ratings breakdown (see ProductDetailSerializer).
        stars = [5, 4, 3, 2, 1]
        distribution = {str(s): round(pct / 100 * count) for s, pct in zip(stars, breakdown_pct)}
        avg = sum(s * int(distribution[str(s)]) for s in stars) / max(1, count)
        product.rating_average = round(avg, 2)
        product.rating_count = count
        product.rating_distribution = distribution
        product.save(update_fields=["rating_average", "rating_count", "rating_distribution"])

    def _seed_license_skus(self, product, revit_years):
        """One activation SKU per Revit year, code compatible with the field convention."""
        for year in revit_years:
            code = f"{product.slug}-{year}-online"
            LicensedProduct.objects.update_or_create(
                code=code,
                defaults={
                    "product": product,
                    "name": f"{product.name} ({year})",
                    "revit_year": year,
                    "default_trial_days": product.default_trial_days,
                    "is_active": True,
                    "price": product.price,
                    "currency": product.currency,
                },
            )

    @staticmethod
    def _slug(name):
        from django.utils.text import slugify

        return slugify(name)
