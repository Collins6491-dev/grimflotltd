"""Authenticated checkout and private order-history views."""

from __future__ import annotations

import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.cart.services import get_cart, totals
from apps.payments.models import PaymentTransaction
from apps.payments.services import PaymentProviderError, initialize_payment

from .forms import CheckoutForm
from .models import DeliveryAddress, Order
from .services import CheckoutError, create_pending_order


def _payment_reference(order: Order) -> str:
    """Make a provider-safe id without exposing predictable order sequencing."""
    return f"GFLPAY-{order.reference}-{secrets.token_hex(5).upper()}"


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    """Reserve inventory and create an unpaid order before provider redirection."""
    cart = get_cart(request, create=False)
    if not cart or not cart.items.exists():
        messages.info(request, "Your cart is empty. Add a product before checkout.")
        return redirect("cart:detail")

    addresses = DeliveryAddress.objects.filter(user=request.user)
    selected = request.GET.get("address")
    address = addresses.filter(pk=selected).first() if selected else addresses.filter(is_default=True).first()
    form = CheckoutForm(request.POST or None, initial=CheckoutForm.from_address(address).initial if address and request.method == "GET" else None)
    if request.method == "POST" and form.is_valid():
        try:
            order = create_pending_order(user=request.user, cart=cart, checkout_data=form.cleaned_data)
        except CheckoutError as error:
            form.add_error(None, str(error))
        else:
            if form.cleaned_data["save_address"]:
                address_data = {
                    field: form.cleaned_data[field]
                    for field in ("recipient_name", "recipient_phone", "address_line_1", "address_line_2", "city", "state", "country")
                }
                DeliveryAddress.objects.update_or_create(
                    user=request.user,
                    address_line_1=address_data["address_line_1"],
                    city=address_data["city"],
                    defaults=address_data,
                )
            return redirect("orders:begin-payment", reference=order.reference)
    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "addresses": addresses,
            "cart": cart,
            "cart_totals": totals(cart),
            "page_title": "Checkout",
            "meta_description": "Secure GRIMFLOT LTD checkout.",
        },
    )


@login_required
@require_http_methods(["GET"])
def begin_payment(request, reference: str):
    """Create or resume payment without trusting a browser-supplied amount."""
    order = get_object_or_404(Order.objects.select_related("user"), reference=reference, user=request.user)
    if order.status != Order.PENDING_PAYMENT:
        return redirect("orders:confirmation", reference=order.reference)
    transaction_record = PaymentTransaction.objects.filter(
        order=order, status__in=(PaymentTransaction.INITIALIZED, PaymentTransaction.PENDING)
    ).order_by("-created_at").first()
    if transaction_record is None:
        try:
            transaction_record = PaymentTransaction.objects.create(
                order=order,
                reference=_payment_reference(order),
                expected_amount=order.total,
                currency=order.currency,
            )
        except IntegrityError:
            transaction_record = PaymentTransaction.objects.filter(order=order).latest("created_at")
    callback_url = request.build_absolute_uri(reverse("payments:callback"))
    try:
        authorization_url = initialize_payment(transaction_record=transaction_record, callback_url=callback_url)
    except PaymentProviderError as error:
        messages.error(request, str(error))
        return redirect("orders:detail", reference=order.reference)
    return redirect(authorization_url)


@login_required
@require_http_methods(["GET"])
def order_list(request):
    orders = request.user.orders.prefetch_related("items", "payments").all()
    return render(request, "orders/order_list.html", {"orders": orders, "page_title": "Your orders"})


@login_required
@require_http_methods(["GET"])
def order_detail(request, reference: str):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "payments", "status_events__actor"),
        reference=reference,
        user=request.user,
    )
    return render(request, "orders/order_detail.html", {"order": order, "page_title": f"Order {order.reference}"})


@login_required
@require_http_methods(["GET"])
def order_confirmation(request, reference: str):
    order = get_object_or_404(Order.objects.prefetch_related("items", "payments"), reference=reference, user=request.user)
    if order.status == Order.PENDING_PAYMENT:
        messages.info(request, "Your order is awaiting payment confirmation.")
    return render(request, "orders/confirmation.html", {"order": order, "page_title": "Order confirmation"})
