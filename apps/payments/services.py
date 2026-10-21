"""Small, explicit Paystack adapter with strict verification invariants."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.services import settle_paid_order

from .models import PaymentTransaction


logger = logging.getLogger(__name__)
PAYSTACK_API = "https://api.paystack.co"


class PaymentProviderError(Exception):
    """A provider outage or malformed response that is safe to show generically."""


def amount_in_subunits(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _request(path: str, *, data: dict | None = None) -> dict:
    secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not secret:
        raise PaymentProviderError("Online payment is not configured yet.")
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = Request(
        f"{PAYSTACK_API}{path}",
        data=body,
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urlopen(request, timeout=12) as response:  # nosec B310: fixed provider endpoint
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        logger.warning("Paystack request failed: %s", type(error).__name__)
        raise PaymentProviderError("The payment provider is temporarily unavailable.") from error
    if not payload.get("status"):
        raise PaymentProviderError("The payment provider could not start this transaction.")
    return payload.get("data") or {}


def initialize_payment(*, transaction_record: PaymentTransaction, callback_url: str) -> str:
    """Start a provider checkout; no order is marked paid at this point."""
    data = _request(
        "/transaction/initialize",
        data={
            "email": transaction_record.order.email,
            "amount": amount_in_subunits(transaction_record.expected_amount),
            "currency": transaction_record.currency,
            "reference": transaction_record.reference,
            "callback_url": callback_url,
            "metadata": {"order_reference": transaction_record.order.reference},
        },
    )
    authorization_url = data.get("authorization_url")
    if not authorization_url:
        raise PaymentProviderError("The payment provider returned an incomplete checkout response.")
    transaction_record.status = PaymentTransaction.PENDING
    transaction_record.provider_payload = {"initialization": data}
    transaction_record.save(update_fields=("status", "provider_payload", "updated_at"))
    return authorization_url


@transaction.atomic
def verify_and_settle(*, transaction_record: PaymentTransaction) -> PaymentTransaction:
    """Verify provider facts server-side before changing money or stock state."""
    locked = PaymentTransaction.objects.select_for_update().select_related("order").get(pk=transaction_record.pk)
    if locked.status == PaymentTransaction.SUCCESS:
        return locked
    data = _request(f"/transaction/verify/{locked.reference}")
    expected = amount_in_subunits(locked.expected_amount)
    if data.get("status") != "success":
        locked.status = PaymentTransaction.FAILED
        locked.failure_reason = "Provider did not report a successful transaction."
        locked.provider_payload = {"verification": data}
        locked.save(update_fields=("status", "failure_reason", "provider_payload", "updated_at"))
        return locked
    if data.get("reference") != locked.reference or data.get("currency") != locked.currency or data.get("amount") != expected:
        logger.error("Rejected payment verification for %s because provider facts did not match.", locked.reference)
        locked.status = PaymentTransaction.FAILED
        locked.failure_reason = "Verified payment facts did not match the order."
        locked.provider_payload = {"verification": data}
        locked.save(update_fields=("status", "failure_reason", "provider_payload", "updated_at"))
        return locked
    locked.status = PaymentTransaction.SUCCESS
    locked.provider_transaction_id = str(data.get("id", ""))
    locked.provider_payload = {"verification": data}
    locked.verified_at = timezone.now()
    locked.save(
        update_fields=("status", "provider_transaction_id", "provider_payload", "verified_at", "updated_at")
    )
    settle_paid_order(order=locked.order)
    return locked
