"""Verified-purchase reviews; public approval remains a staff action."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

from .forms import ProductReviewForm
from .models import ProductReview


@login_required
@require_POST
def submit_product_review(request, slug: str):
    product = get_object_or_404(Product, slug=slug, is_published=True, category__is_published=True)
    is_verified_purchase = OrderItem.objects.filter(
        product=product,
        order__user=request.user,
        order__status__in=(Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.COMPLETED),
    ).exists()
    if not is_verified_purchase:
        return HttpResponseForbidden("Only verified purchasers can review this product.")

    existing = ProductReview.objects.filter(product=product, user=request.user).first()
    form = ProductReviewForm(request.POST, instance=existing)
    if not form.is_valid():
        messages.error(request, "Please complete your rating, title, and review before submitting it.")
        return redirect(product.get_absolute_url())
    review = form.save(commit=False)
    review.product = product
    review.user = request.user
    # A changed review must be moderated again; publication is never self-service.
    review.status = ProductReview.PENDING
    review.save()
    messages.success(request, "Thank you. Your review has been submitted for moderation.")
    return redirect(product.get_absolute_url())
