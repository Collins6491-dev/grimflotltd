"""Paystack callback and signed webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.orders.services import cancel_unpaid_order

from .models import PaymentTransaction, WebhookEvent
from .services import PaymentProviderError, verify_and_settle


logger = logging.getLogger(__name__)


@login_required
@require_GET
def payment_callback(request):
    """Verify callback facts at the provider before showing a customer result."""
    reference = request.GET.get("reference", "")
    transaction_record = get_object_or_404(
        PaymentTransaction.objects.select_related("order"), reference=reference, order__user=request.user
    )
    try:
        verified = verify_and_settle(transaction_record=transaction_record)
    except PaymentProviderError:
        messages.warning(request, "We could not confirm payment yet. Please refresh the order shortly.")
        return redirect("orders:detail", reference=transaction_record.order.reference)
    if verified.status == PaymentTransaction.SUCCESS:
        messages.success(request, "Payment verified. Your order is now in our fulfilment queue.")
    else:
        cancel_unpaid_order(
            order=verified.order,
            reason="Provider reported an unsuccessful payment.",
        )
        messages.error(request, "Payment was not successful. No charge has been accepted by GRIMFLOT LTD.")
    return redirect("orders:confirmation", reference=verified.order.reference)


def _is_valid_signature(raw_body: bytes, signature: str) -> bool:
    secret = getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "") or getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Accept a signed charge event once; amount and currency remain provider-verified."""
    raw_body = request.body
    if not _is_valid_signature(raw_body, request.headers.get("X-Paystack-Signature", "")):
        return HttpResponseForbidden("Invalid webhook signature.")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid JSON payload.")
    event_type = payload.get("event", "")
    data = payload.get("data") or {}
    reference = str(data.get("reference", ""))
    if event_type != "charge.success" or not reference:
        return JsonResponse({"received": True})
    event_id = f"{event_type}:{reference}"
    with transaction.atomic():
        event, created = WebhookEvent.objects.select_for_update().get_or_create(
            provider=PaymentTransaction.PAYSTACK,
            event_id=event_id,
            defaults={"event_type": event_type, "payload": payload},
        )
    if not created and event.processed_at:
        return JsonResponse({"received": True, "duplicate": True})
    transaction_record = PaymentTransaction.objects.select_related("order").filter(reference=reference).first()
    if not transaction_record:
        logger.warning("Ignored signed Paystack event with unknown reference.")
        event.processed_at = timezone.now()
        event.save(update_fields=("processed_at", "updated_at"))
        return JsonResponse({"received": True})
    try:
        verified = verify_and_settle(transaction_record=transaction_record)
    except PaymentProviderError:
        logger.warning("Paystack verification temporarily failed for webhook reference %s", reference)
        # Allow the provider retry to be handled manually only after a staff review;
        # retain the raw accepted event for audit rather than trusting it as payment proof.
        return JsonResponse({"received": True}, status=202)
    if verified.status != PaymentTransaction.SUCCESS:
        cancel_unpaid_order(
            order=verified.order,
            reason="Provider reported an unsuccessful payment.",
        )
    event.processed_at = timezone.now()
    event.save(update_fields=("processed_at", "updated_at"))
    return JsonResponse({"received": True})
