"""
Collapse the storefront taxonomy down to a single top-level category.

The marketplace only sells Revit plugins, so the flat list of sibling
categories (Automation Tools, Dynamo Scripts, BIM Libraries, ...) is replaced by
ONE root — "Revit Plugins" — under which staff define their own subcategories
from the admin (Category.parent has always supported this; nothing used it).

Every product is re-pointed at the root before the old categories are removed,
so no product loses its category and Product.category's PROTECT never fires.
Deliberately one-way: reversing it can't know which category each product came
from, so the reverse is a no-op rather than a lie.
"""
from django.db import migrations

ROOT_NAME = "Revit Plugins"
ROOT_SLUG = "revit-plugins"
ROOT_ICON = "puzzle"


def collapse(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    if not Category.objects.exists():
        # Nothing to collapse. A fresh database (a test run, a new environment)
        # gets its taxonomy from the seed command or the admin — a data
        # migration has no business inventing content that isn't there.
        return

    root = Category.objects.filter(slug=ROOT_SLUG).first() or Category.objects.filter(name=ROOT_NAME).first()
    if root is None:
        root = Category.objects.create(
            name=ROOT_NAME, slug=ROOT_SLUG, icon=ROOT_ICON, sort_order=0
        )
    elif root.parent_id or root.sort_order:
        root.parent = None
        root.sort_order = 0
        root.save(update_fields=["parent", "sort_order"])

    Product.objects.exclude(category_id=root.pk).update(category_id=root.pk)
    # Children go with their parents (Category.parent is CASCADE), so deleting
    # the other roots is enough to clear the whole old tree.
    Category.objects.exclude(pk=root.pk).delete()


def noop(apps, schema_editor):
    """Irreversible in substance — the old categories and which product sat in
    which are gone. Declared so the migration can still be unapplied."""


class Migration(migrations.Migration):

    dependencies = [("catalog", "0013_product_monthly_price_product_yearly_price")]

    operations = [migrations.RunPython(collapse, noop)]
