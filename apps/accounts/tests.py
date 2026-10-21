from django.test import TestCase

from .models import User


class UserModelTests(TestCase):
    def test_email_is_the_login_identifier(self):
        user = User.objects.create_user("customer@example.com", "secure-passphrase-123")

        self.assertEqual(user.email, "customer@example.com")
        self.assertTrue(user.check_password("secure-passphrase-123"))
        self.assertEqual(User.USERNAME_FIELD, "email")
