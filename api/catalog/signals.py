"""
Keeps the licensing activation SKU in lockstep with its storefront Product.
Runs on every save from any code path (admin portal, Django admin, shell,
seed script) so licensing "just works" without every write path having to
remember to call the sync function itself.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.models import Product


@receiver(post_save, sender=Product)
def sync_product_license_sku(sender, instance, **kwargs):
    from licensing.services import sync_license_sku

    sync_license_sku(instance)
