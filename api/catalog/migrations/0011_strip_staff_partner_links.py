from django.db import migrations


def strip_staff_partners(apps, schema_editor):
    """One-time cleanup: before BecomeSellerView blocked it, a staff account
    could apply to become a seller. Staff must never be partners — remove the
    link, the partner's own data (logo/tagline/bio/etc.), and any products
    created under that partner."""
    User = apps.get_model("accounts", "User")
    Product = apps.get_model("catalog", "Product")
    Partner = apps.get_model("catalog", "Partner")

    partner_ids = list(
        User.objects.filter(is_staff=True, partner__isnull=False).values_list("partner_id", flat=True)
    )
    if not partner_ids:
        return

    Product.objects.filter(partner_id__in=partner_ids).delete()
    User.objects.filter(is_staff=True, partner_id__in=partner_ids).update(partner=None)
    Partner.objects.filter(id__in=partner_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_partner_rejection_note_partner_status_and_more"),
        ("accounts", "0004_remove_user_must_change_password_alter_user_partner"),
    ]

    operations = [
        migrations.RunPython(strip_staff_partners, migrations.RunPython.noop),
    ]
