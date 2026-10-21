"""Consultation requests remain pending until a staff member confirms them."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.security import rate_limit

from .forms import ConsultationBookingForm


@rate_limit("consultation", limit=5, window=900)
@require_http_methods(["GET", "POST"])
def consultation(request):
    form = ConsultationBookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your consultation request is pending confirmation. We will contact you to agree the final appointment time.")
        return redirect("bookings:consultation")
    return render(
        request,
        "bookings/consultation.html",
        {"form": form, "page_title": "Book a consultation"},
    )
