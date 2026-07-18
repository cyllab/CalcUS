from io import StringIO

from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .forms import CreateFullAccountForm, ResearcherCreateForm
from .models import User


class CaseInsensitiveEmailTests(TestCase):
    password = "A-secure-password-123!"

    def test_user_manager_normalizes_entire_email_address(self):
        user = User.objects.create_user(
            email="Mixed.Case@Example.COM",
            password=self.password,
        )

        self.assertEqual(user.email, "mixed.case@example.com")

    def test_existing_mixed_case_user_can_log_in_with_any_casing(self):
        user = User.objects.create_user(
            email="mixed.case@example.com",
            password=self.password,
        )
        User.objects.filter(pk=user.pk).update(email="Mixed.Case@Example.com")

        authenticated_user = authenticate(
            email="MIXED.CASE@EXAMPLE.COM",
            password=self.password,
        )

        self.assertEqual(authenticated_user.pk, user.pk)

    def test_researcher_registration_stores_lowercase_email(self):
        form = ResearcherCreateForm(
            data={
                "email": "New.Researcher@Example.COM",
                "password1": self.password,
                "password2": self.password,
                "tos": True,
            }
        )
        form.fields.pop("captcha", None)

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "new.researcher@example.com")

    def test_researcher_registration_rejects_case_variant(self):
        User.objects.create_user(
            email="researcher@example.com",
            password=self.password,
        )
        form = ResearcherCreateForm(
            data={
                "email": "Researcher@EXAMPLE.COM",
                "password1": self.password,
                "password2": self.password,
                "tos": True,
            }
        )
        form.fields.pop("captcha", None)

        self.assertFalse(form.is_valid())
        self.assertIn("already been used", form.errors["email"][0])

    def test_full_account_registration_rejects_case_variant(self):
        User.objects.create_user(
            email="researcher@example.com",
            password=self.password,
        )
        temporary_user = User.objects.create_user(
            email="temporary@calcus.cloud",
            password=self.password,
            is_temporary=True,
        )
        form = CreateFullAccountForm(
            temporary_user,
            data={
                "email": "Researcher@EXAMPLE.COM",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("already been used", form.errors["email"][0])


class EmailCaseDuplicateCommandTests(TestCase):
    password = "A-secure-password-123!"

    def test_command_reports_no_duplicates(self):
        User.objects.create_user(
            email="unique@example.com",
            password=self.password,
        )
        stdout = StringIO()

        call_command("check_email_case_duplicates", stdout=stdout)

        self.assertIn("No case-insensitive duplicate", stdout.getvalue())

    def test_command_reports_case_insensitive_duplicates(self):
        mixed_case_user = User.objects.create_user(
            email="first@example.com",
            password=self.password,
        )
        User.objects.filter(pk=mixed_case_user.pk).update(email="User@Example.com")
        lowercase_user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
        )
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command("check_email_case_duplicates", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("Found 1 duplicate email group", output)
        self.assertIn("User@Example.com", output)
        self.assertIn("user@example.com", output)
        self.assertIn(str(mixed_case_user.pk), output)
        self.assertIn(str(lowercase_user.pk), output)
        self.assertIn("last_login=never", output)
        self.assertIn("calculations=0", output)


@override_settings(IS_CLOUD=True)
class LoginFeedbackTests(TestCase):
    password = "A-secure-password-123!"

    def test_login_page_contains_recaptcha_load_warning(self):
        response = self.client.get("/accounts/login/")

        self.assertContains(response, "Security verification could not load.")
        self.assertContains(response, 'id="recaptcha-load-warning"')

    def test_captcha_error_is_not_reported_as_bad_credentials(self):
        User.objects.create_user(
            email="user@example.com",
            password=self.password,
        )

        response = self.client.post(
            "/accounts/login/",
            data={"username": "user@example.com", "password": self.password},
        )

        self.assertContains(response, "Security verification failed.")
        self.assertNotContains(response, "We couldn't sign you in with that email")
