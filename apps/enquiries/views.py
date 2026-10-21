"""Rate-limited enquiry capture that gives staff a trackable work item."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.security import rate_limit

from .forms import EnquiryForm
from .models import Enquiry


def _handle(request, *, enquiry_type: str, title: str, intro: str):
    form = EnquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.enquiry_type = enquiry_type
        enquiry.save()
        messages.success(request, "Your request has been received. A member of our team will respond using your chosen contact details.")
        return redirect(request.path)
    return render(request, "enquiries/form.html", {"form": form, "page_title": title, "intro": intro, "enquiry_type": enquiry_type})


@rate_limit("contact", limit=6, window=900)
@require_http_methods(["GET", "POST"])
def contact(request):
    return _handle(request, enquiry_type=Enquiry.CONTACT, title="Contact GRIMFLOT LTD", intro="Tell us what you are planning and the technical context around it.")


@rate_limit("quote", limit=5, window=900)
@require_http_methods(["GET", "POST"])
def quote_request(request):
    return _handle(request, enquiry_type=Enquiry.QUOTE, title="Request a quotation", intro="Share the system, property, or installation scope you would like us to assess.")
