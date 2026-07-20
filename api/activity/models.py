"""
A single append-only log of "who did what, when" across the storefront and admin
portal — sign-ins, purchases/claims, downloads, reviews, and staff actions on
products/licenses/orders. Intentionally denormalized (actor_label, target_label are
plain strings) so entries stay readable even if the user or product they reference
is later deleted or renamed.
"""
from django.conf import settings
from django.db import models


class ActivityVerb(models.TextChoices):
    SIGNED_IN = "signed_in", "Signed in"
    SIGNED_UP = "signed_up", "Signed up"
    CLAIMED_FREE_PRODUCT = "claimed_free_product", "Claimed a free product"
    ORDER_PLACED = "order_placed", "Placed an order"
    ORDER_REFUND_REQUESTED = "order_refund_requested", "Requested a refund"
    DOWNLOADED_FILE = "downloaded_file", "Downloaded a file"
    POSTED_REVIEW = "posted_review", "Posted a review"
    PRODUCT_CREATED = "product_created", "Created a product"
    PRODUCT_UPDATED = "product_updated", "Updated a product"
    PRODUCT_DELETED = "product_deleted", "Deleted a product"
    PRODUCT_SUBMITTED_FOR_REVIEW = "product_submitted_for_review", "Submitted a product for review"
    PRODUCT_APPROVED = "product_approved", "Approved a product"
    PRODUCT_REJECTED = "product_rejected", "Rejected a product"
    LICENSE_REVOKED = "license_revoked", "Revoked a license"
    LICENSE_RESTORED = "license_restored", "Restored a license"
    LICENSE_EXTENDED = "license_extended", "Extended a license"
    LICENSE_RELEASED = "license_released", "Released a machine binding"
    ORDER_STATUS_CHANGED = "order_status_changed", "Changed an order's status"
    ORDER_SEATS_CHANGED = "order_seats_changed", "Changed an order's seat count"
    LICENSE_CODE_CREATED = "license_code_created", "Generated a license code"
    LICENSE_CODE_REVOKED = "license_code_revoked", "Revoked a license code"
    REDEEMED_LICENSE_CODE = "redeemed_license_code", "Redeemed a license code"


class ActivityLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_log"
    )
    actor_label = models.CharField(max_length=180, blank=True, help_text="Snapshot of the actor's email/name.")
    verb = models.CharField(max_length=40, choices=ActivityVerb.choices)
    target_label = models.CharField(max_length=200, blank=True, help_text="What the action was performed on.")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["verb"]),
        ]

    def __str__(self):
        return f"{self.actor_label or 'System'} {self.verb} {self.target_label}".strip()
