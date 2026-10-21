"""Account messages whose links must only be generated server-side."""

from __future__ import annotations

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse


VERIFY_SALT = "grimflot.accounts.verify-email"


def verification_token(user) -> str:
    return signing.dumps({"user_id": user.pk, "email": user.email}, salt=VERIFY_SALT)


def send_verification_email(*, user, request) -> None:
    token = verification_token(user)
    path = reverse("accounts:verify-email", kwargs={"token": token})
    url = request.build_absolute_uri(path)
    send_mail(
        subject="Verify your GRIMFLOT LTD email address",
        message=(
            "Welcome to GRIMFLOT LTD. Verify your email address before checkout:\n\n"
            f"{url}\n\nThis link expires in 48 hours."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
