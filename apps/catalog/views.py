"""Public, read-only views for product discovery."""

from __future__ import annotations

from django.urls import reverse
from django.views.generic import DetailView, ListView

from apps.cart.forms import AddToCartForm
from apps.orders.models import OrderItem, Order
from apps.reviews.forms import ProductReviewForm
from apps.reviews.models import ProductReview

from .forms import CatalogueFilterForm
from .models import Category, Product
from .selectors import published_products


class ProductListView(ListView):
    """Browse a paginated catalogue without exposing unpublished products."""

    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_filter_form(self) -> CatalogueFilterForm:
        if not hasattr(self, "_filter_form"):
            categories = Category.objects.filter(is_published=True).order_by("order", "name")
            self._filter_form = CatalogueFilterForm(self.request.GET or None, categories=categories)
        return self._filter_form

    def get_queryset(self):
        filter_form = self.get_filter_form()
        filters = filter_form.cleaned_data if filter_form.is_valid() else {}
        return published_products(filters=filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_parameters = self.request.GET.copy()
        query_parameters.pop("page", None)
        context.update(
            {
                "filter_form": self.get_filter_form(),
                "active_query": query_parameters.urlencode(),
                "page_title": "Products",
                "meta_description": "Browse GRIMFLOT LTD smart technology, energy, security, and electrical products.",
                "canonical_url": self.request.build_absolute_uri(reverse("catalogue:product-list")),
            }
        )
        return context


class ProductDetailView(DetailView):
    """Show one published product and compatible related discoveries."""

    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return published_products().prefetch_related("specifications")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context.update(
            {
                "related_products": published_products()
                .filter(category=product.category)
                .exclude(pk=product.pk)[:4],
                "page_title": product.meta_title or product.name,
                "meta_description": product.meta_description or product.short_description,
                "canonical_url": self.request.build_absolute_uri(product.get_absolute_url()),
                "add_to_cart_form": AddToCartForm(),
            }
        )
        if self.request.user.is_authenticated:
            context["is_wishlisted"] = self.request.user.wishlist_items.filter(product=product).exists()
            context["can_review"] = OrderItem.objects.filter(
                product=product,
                order__user=self.request.user,
                order__status__in=(Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.COMPLETED),
            ).exists()
            if context["can_review"]:
                existing_review = ProductReview.objects.filter(product=product, user=self.request.user).first()
                context["review_form"] = ProductReviewForm(instance=existing_review)
        context["approved_reviews"] = ProductReview.objects.filter(
            product=product, status=ProductReview.APPROVED
        ).select_related("user")
        return context
