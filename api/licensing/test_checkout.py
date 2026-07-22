"""
Checkout — now actually collects payment via Paymob (see
licensing/account_api.py::CheckoutView/CheckoutStatusView/PaymobWebhookView
and licensing/paymob.py). A checkout call only ever creates PENDING
purchases; nothing becomes PAID until a webhook call with a valid HMAC
signature says so — these tests simulate that webhook with a real computed
signature rather than trusting the redirect alone, same as production code
does. licensing.paymob.create_intention is mocked throughout (no real
network calls to Paymob from the test suite) — its own logic (HMAC calc,
error handling) is covered directly in test_paymob.py.

The main behavior worth locking in: one purchase per unit bought — buying
qty=3 of the same product creates three independent purchases, each its
own license_key, seats=1. One key per seat, deliberately, so each copy
activates its own machine.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from licensing import paymob
from licensing.models import ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Checkout Test", product_code="checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="49.00",
    )


@pytest.fixture
def second_product(category):
    return Product.objects.create(
        name="Second Checkout Test", product_code="checkout-test-2", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="19.00",
    )


@pytest.fixture
def buyer_client():
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture(autouse=True)
def _paymob_settings(settings):
    settings.PAYMOB_HMAC_SECRET = "test-hmac-secret"


@pytest.fixture
def mock_intention():
    with patch("licensing.account_api.paymob.create_intention") as mocked:
        mocked.return_value = {"client_secret": "cs_test_fake"}
        yield mocked


def _checkout(client, items):
    return client.post("/api/account/checkout", data={"items": items}, content_type="application/json")


def _webhook_payload(reference, *, success=True, pending=False, extra=None):
    obj = {
        "amount_cents": 4900, "created_at": "2026-01-01T00:00:00Z", "currency": "EGP",
        "error_occured": False, "has_parent_transaction": False, "id": 1,
        "integration_id": 1, "is_3d_secure": True, "is_auth": False, "is_capture": False,
        "is_refunded": False, "is_standalone_payment": True, "is_voided": False,
        "order": {"id": 1}, "owner": 1, "pending": pending,
        "source_data": {"pan": "1234", "sub_type": "MasterCard", "type": "card"},
        "success": success, "special_reference": reference,
        **(extra or {}),
    }
    return obj


def _send_webhook(client, obj, *, valid_hmac=True):
    hmac_value = paymob.compute_hmac(obj) if valid_hmac else "0" * 128
    return client.post(
        f"/api/webhooks/paymob?hmac={hmac_value}",
        data={"type": "TRANSACTION", "obj": obj},
        content_type="application/json",
    )


# ── Checkout: creates PENDING purchases + a Paymob intention ──
def test_checkout_creates_pending_purchases_and_returns_a_checkout_url(buyer_client, product, mock_intention):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 1}])
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["checkoutUrl"].startswith("https://accept.paymob.com/unifiedcheckout/")
    assert body["reference"]

    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PENDING
    assert purchase.payment_reference == body["reference"]
    assert purchase.expires_at is None  # set by the webhook, not here
    mock_intention.assert_called_once()
    assert mock_intention.call_args.kwargs["amount_cents"] == 4900


def test_buying_three_of_the_same_product_creates_three_separate_keys(buyer_client, product, mock_intention):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 3}])
    assert resp.status_code == 201, resp.json()

    purchases = list(ProductPurchase.objects.filter(user=user, product__product=product))
    assert len(purchases) == 3
    assert len({p.license_key for p in purchases}) == 3  # every key is distinct
    for purchase in purchases:
        assert purchase.seats == 1
        assert purchase.payment_status == ProductPurchase.PaymentStatus.PENDING
        assert str(purchase.amount) == "49.00"  # unit price, not qty * price
        assert purchase.payment_reference == resp.json()["reference"]  # same order


def test_checkout_creates_one_purchase_per_unit_across_distinct_products(buyer_client, product, second_product, mock_intention):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 1}, {"slug": second_product.slug, "qty": 2}])
    assert resp.status_code == 201, resp.json()
    assert ProductPurchase.objects.filter(user=user, product__product=product).count() == 1
    assert ProductPurchase.objects.filter(user=user, product__product=second_product).count() == 2
    # 49.00 + 2*19.00 = 87.00 -> 8700 cents, sent as one combined intention
    assert mock_intention.call_args.kwargs["amount_cents"] == 8700


def test_checking_out_again_adds_more_separate_purchases(buyer_client, product, mock_intention):
    client, user = buyer_client
    _checkout(client, [{"slug": product.slug, "qty": 1}])
    resp = _checkout(client, [{"slug": product.slug, "qty": 2}])
    assert resp.status_code == 201, resp.json()

    purchases = list(ProductPurchase.objects.filter(user=user, product__product=product))
    assert len(purchases) == 3  # 1 from the first checkout + 2 from the second
    assert len({p.license_key for p in purchases}) == 3


def test_retrying_checkout_cancels_the_previous_attempts_pending_purchases(buyer_client, product, mock_intention):
    # A customer whose card gets declined (or who just abandons the Paymob
    # page) and then retries used to leave the first attempt's PENDING
    # purchases stranded forever — every retry piled on more unusable keys.
    # A fresh checkout call now closes out any of the user's still-PENDING
    # purchases from earlier attempts instead of leaving them dangling.
    client, user = buyer_client
    first = _checkout(client, [{"slug": product.slug, "qty": 1}])
    first_purchase = ProductPurchase.objects.get(user=user, product__product=product)

    second = _checkout(client, [{"slug": product.slug, "qty": 1}])
    assert second.status_code == 201, second.json()

    first_purchase.refresh_from_db()
    assert first_purchase.payment_status == ProductPurchase.PaymentStatus.CANCELLED
    new_purchase = ProductPurchase.objects.get(payment_reference=second.json()["reference"])
    assert new_purchase.payment_status == ProductPurchase.PaymentStatus.PENDING


def test_a_late_webhook_for_a_cancelled_attempt_still_grants_the_license(buyer_client, product, mock_intention):
    # If Paymob reports the OLD (now-cancelled-by-retry) attempt actually
    # succeeded, the webhook should still honor it — our local bookkeeping
    # status shouldn't override what really happened at the payment gateway.
    client, user = buyer_client
    first = _checkout(client, [{"slug": product.slug, "qty": 1}])
    first_reference = first.json()["reference"]
    _checkout(client, [{"slug": product.slug, "qty": 1}])  # supersedes/cancels the first

    first_purchase = ProductPurchase.objects.get(payment_reference=first_reference)
    assert first_purchase.payment_status == ProductPurchase.PaymentStatus.CANCELLED

    resp = _send_webhook(client, _webhook_payload(first_reference, success=True))
    assert resp.status_code == 200
    first_purchase.refresh_from_db()
    assert first_purchase.payment_status == ProductPurchase.PaymentStatus.PAID


def test_checkout_requires_login(product):
    resp = _checkout(Client(), [{"slug": product.slug, "qty": 1}])
    assert resp.status_code in (401, 403)


def test_checkout_rejects_an_empty_cart(buyer_client):
    client, _ = buyer_client
    resp = _checkout(client, [])
    assert resp.status_code == 400


def test_checkout_rejects_an_unknown_slug(buyer_client):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": "does-not-exist", "qty": 1}])
    assert resp.status_code == 400


def test_checkout_rejects_an_unpublished_product(buyer_client, category):
    draft = Product.objects.create(
        name="Draft Checkout Test", product_code="draft-checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.DRAFT, price="10.00",
    )
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": draft.slug, "qty": 1}])
    assert resp.status_code == 400


def test_checkout_works_for_a_free_product_too(buyer_client, category, mock_intention):
    free_product = Product.objects.create(
        name="Free Checkout Test", product_code="free-checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED, price="0.00",
    )
    client, user = buyer_client
    resp = _checkout(client, [{"slug": free_product.slug, "qty": 1}])
    assert resp.status_code == 201, resp.json()
    purchase = ProductPurchase.objects.get(user=user, product__product=free_product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PENDING
    assert str(purchase.amount) == "0.00"


def test_checkout_returns_a_clean_400_when_paymob_isnt_configured(buyer_client, product):
    client, _ = buyer_client
    with patch("licensing.account_api.paymob.create_intention", side_effect=paymob.PaymobError("not configured")):
        resp = _checkout(client, [{"slug": product.slug, "qty": 1}])
    assert resp.status_code == 400
    # The PENDING purchases created before the (failing) Paymob call stay
    # orphaned/PENDING rather than being rolled back — acceptable for a
    # config error a customer can just retry; not what this test checks.


# ── Webhook: the only thing that ever grants PAID access ──
def test_webhook_with_a_valid_signature_marks_matching_purchases_paid(buyer_client, product, mock_intention):
    client, user = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    resp = _send_webhook(Client(), _webhook_payload(reference))
    assert resp.status_code == 200, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert purchase.paid_at is not None
    assert purchase.expires_at is None  # one-time purchase, perpetual


def test_webhook_captures_masked_card_details_for_payment_methods_history(buyer_client, product, mock_intention):
    # Powers /account/payment-methods (see AccountPaymentMethodListView) —
    # only ever the masked last 4 digits Paymob itself sends back, never a
    # full card number.
    client, user = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    resp = _send_webhook(Client(), _webhook_payload(reference))
    assert resp.status_code == 200, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    assert purchase.card_brand == "MasterCard"
    assert purchase.card_last4 == "1234"


def test_webhook_sets_expires_at_for_a_monthly_purchase(buyer_client, category, mock_intention):
    sub = Product.objects.create(
        name="Sub Webhook Test", product_code="sub-webhook-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="0.00", monthly_price="19.00", yearly_price="179.00",
    )
    client, user = buyer_client
    reference = _checkout(client, [{"slug": sub.slug, "qty": 1, "billingPeriod": "monthly"}]).json()["reference"]

    _send_webhook(Client(), _webhook_payload(reference))

    purchase = ProductPurchase.objects.get(user=user, product__product=sub)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert purchase.expires_at is not None  # TEMPORARY test override: 10 minutes, not 30 days — see
    # _subscription_duration() in account_api.py. Just checking it's set at
    # all here; the exact duration is asserted in test_account_api-adjacent
    # tests only if that override is ever made configurable.


def test_webhook_with_an_invalid_signature_is_rejected_and_leaves_purchases_pending(buyer_client, product, mock_intention):
    client, user = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    resp = _send_webhook(Client(), _webhook_payload(reference), valid_hmac=False)
    assert resp.status_code == 400

    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PENDING


def test_webhook_for_a_failed_transaction_leaves_purchases_pending(buyer_client, product, mock_intention):
    client, user = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    resp = _send_webhook(Client(), _webhook_payload(reference, success=False))
    assert resp.status_code == 200  # acknowledged, just nothing to grant

    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PENDING


def test_webhook_is_idempotent_on_redelivery(buyer_client, product, mock_intention):
    client, user = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    _send_webhook(Client(), _webhook_payload(reference))
    purchase = ProductPurchase.objects.get(user=user, product__product=product)
    first_paid_at = purchase.paid_at

    resp = _send_webhook(Client(), _webhook_payload(reference))  # Paymob redelivers
    assert resp.status_code == 200

    purchase.refresh_from_db()
    assert purchase.paid_at == first_paid_at  # untouched, not re-processed


def test_webhook_for_an_unknown_reference_is_acknowledged_but_does_nothing():
    resp = _send_webhook(Client(), _webhook_payload("bimhive-does-not-exist"))
    assert resp.status_code == 200


# ── Status polling (used by /checkout/confirmation) ──
def test_checkout_status_reports_pending_before_the_webhook_lands(buyer_client, product, mock_intention):
    client, _ = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    resp = client.get(f"/api/account/checkout/status?reference={reference}")
    assert resp.status_code == 200
    assert resp.json()["pending"] is True


def test_checkout_status_reports_paid_purchases_after_the_webhook(buyer_client, product, mock_intention):
    client, _ = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]
    _send_webhook(Client(), _webhook_payload(reference))

    resp = client.get(f"/api/account/checkout/status?reference={reference}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pending"] is False
    assert len(body["purchases"]) == 1
    assert body["purchases"][0]["license_key"]


def test_checkout_status_requires_login(product):
    resp = Client().get("/api/account/checkout/status?reference=whatever")
    assert resp.status_code in (401, 403)


def test_checkout_status_404s_for_someone_elses_reference(buyer_client, product, mock_intention):
    client, _ = buyer_client
    reference = _checkout(client, [{"slug": product.slug, "qty": 1}]).json()["reference"]

    other = User.objects.create_user(username="other@x.com", email="other@x.com", password="x")
    other_client = Client()
    other_client.force_login(other)
    resp = other_client.get(f"/api/account/checkout/status?reference={reference}")
    assert resp.status_code == 400


# ── Subscription (monthly/yearly) checkout ──
@pytest.fixture
def subscription_product(category):
    return Product.objects.create(
        name="Subscription Test", product_code="subscription-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="0.00", monthly_price="19.00", yearly_price="179.00",
    )


def test_monthly_checkout_prices_the_purchase_at_the_monthly_rate(buyer_client, subscription_product, mock_intention):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "monthly"}])
    assert resp.status_code == 201, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=subscription_product)
    assert str(purchase.amount) == "19.00"
    assert purchase.billing_period == "monthly"


def test_yearly_checkout_prices_the_purchase_at_the_yearly_rate(buyer_client, subscription_product, mock_intention):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "yearly"}])
    assert resp.status_code == 201, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=subscription_product)
    assert str(purchase.amount) == "179.00"
    assert purchase.billing_period == "yearly"


def test_checkout_rejects_a_billing_period_for_a_non_subscription_product(buyer_client, product):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 1, "billingPeriod": "monthly"}])
    assert resp.status_code == 400


def test_checkout_rejects_an_invalid_billing_period(buyer_client, subscription_product):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "weekly"}])
    assert resp.status_code == 400


def test_staff_marking_a_pending_subscription_order_paid_starts_its_billing_period(
    buyer_client, subscription_product, mock_intention, django_user_model
):
    # Admin Orders' existing "Mark Paid" button (AdminOrderStatusView action
    # "restore" -> services.restore_purchase_access) is the only way to test
    # the payment -> license -> revocation flow while blocked on a live
    # Paymob transaction (see paymob-integration project notes). It must
    # compute expires_at the same way the real webhook would, or a
    # subscription "confirmed" this way would look perpetual and never
    # revoke.
    client, user = buyer_client
    _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "monthly"}])
    purchase = ProductPurchase.objects.get(user=user, product__product=subscription_product)
    assert purchase.expires_at is None  # unset until confirmed, same as always

    staff = django_user_model.objects.create_user(username="staff", email="staff@x.com", password="x", is_staff=True)
    staff_client = Client()
    staff_client.force_login(staff)
    resp = staff_client.post(f"/api/admin/orders/{purchase.pk}/status", {"action": "restore"})
    assert resp.status_code == 200, resp.json()

    purchase.refresh_from_db()
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert purchase.expires_at is not None  # now correctly started, not left perpetual


def test_one_time_checkout_of_a_subscription_product_falls_back_to_the_one_time_price(buyer_client, category, mock_intention):
    # A subscription product can still list a one-time price too — omitting
    # billingPeriod entirely just buys it outright, perpetual, same as any
    # other product.
    hybrid = Product.objects.create(
        name="Hybrid Pricing Test", product_code="hybrid-pricing-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="99.00", monthly_price="9.00", yearly_price="89.00",
    )
    client, user = buyer_client
    resp = _checkout(client, [{"slug": hybrid.slug, "qty": 1}])
    assert resp.status_code == 201, resp.json()
    purchase = ProductPurchase.objects.get(user=user, product__product=hybrid)
    assert str(purchase.amount) == "99.00"
    assert purchase.billing_period == ""
