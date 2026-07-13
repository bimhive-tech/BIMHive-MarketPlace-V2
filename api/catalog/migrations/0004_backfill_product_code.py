from django.db import migrations


def backfill_product_code(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    seen = set(Product.objects.exclude(product_code="").values_list("product_code", flat=True))
    for product in Product.objects.filter(product_code=""):
        base = product.slug
        code = base
        counter = 2
        while code in seen:
            code = f"{base}-{counter}"
            counter += 1
        seen.add(code)
        product.product_code = code
        product.save(update_fields=["product_code"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_add_product_code'),
    ]

    operations = [
        migrations.RunPython(backfill_product_code, noop),
    ]
