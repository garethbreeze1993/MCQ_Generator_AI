from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from django.conf import settings

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.messages import get_messages

from unittest.mock import patch, MagicMock

from accounts.tokens import account_activation_token

from accounts.utils import get_ses_client

from django.contrib.auth import get_user_model
from accounts.backends import CustomBackend  # Adjust import path

BackendUser = get_user_model()

class AccountsTestCase(TestCase):


    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password',
                                                 email='testuser@gmail.com')
        cls.inactive_user = User.objects.create_user(username='inactivetestuser', password='password2',
                                                     email="inactive_user@gmail.com")
        cls.inactive_user.is_active = False
        cls.inactive_user.save()

    def setUp(self):
        # Every test needs a client.
        self.authenticated_client = Client()
        self.authenticated_client.login(username='testuser', password='password')
        self.unauthenticated_client = Client()


    def test_login_username_password(self):

        login_url = reverse("login")  # Replace with your login URL name if different
        response = self.unauthenticated_client.post(login_url, {
            "username": "testuser",
            "password": "password"
        })

        # Check for successful redirect (default is 302 on success)
        self.assertEqual(response.status_code, 302)

        success_url = reverse("home")

        self.assertEqual(response.url, success_url)


        # verify that user is authenticated
        self.assertTrue("_auth_user_id" in self.unauthenticated_client.session)

    def test_login_email_password(self):
        login_url = reverse("login")  # Replace with your login URL name if differ
        response = self.unauthenticated_client.post(login_url, {
            "username": "testuser@gmail.com",
            "password": "password"
        })
        # Check for successful redirect (default is 302 on success)
        self.assertEqual(response.status_code, 302)
        success_url = reverse("home")
        self.assertEqual(response.url, success_url)
        # verify that user is authenticated
        self.assertTrue("_auth_user_id" in self.unauthenticated_client.session)

    def test_login_wrong_username(self):

        login_url = reverse("login")  # Replace with your login URL name if different
        response = self.unauthenticated_client.post(login_url, {
            "username": "testusera",
            "password": "password"
        })

        # Check for successful redirect (default is 302 on success)
        self.assertEqual(response.status_code, 200)


        self.assertEqual(response.template_name[0], "registration/login.html")

        self.assertContains(response, "Please enter a correct username and password.")

        # verify that user is authenticated
        self.assertFalse("_auth_user_id" in self.unauthenticated_client.session)

    def test_login_wrong_password(self):
        login_url = reverse("login")  # Replace with your login URL name if diffe
        response = self.unauthenticated_client.post(login_url, {
            "username": "testuser",
            "password": "passworddd"
        })
        # Check for successful redirect (default is 302 on success)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "registration/login.html")
        self.assertContains(response, "Please enter a correct username and password")
        # verify that user is authenticated
        self.assertFalse("_auth_user_id" in self.unauthenticated_client.session)

    def test_login_inactive_user(self):
        login_url = reverse("login")  # Replace with your login URL name if diffe
        response = self.unauthenticated_client.post(login_url, {
            "username": "inactivetestuser",
            "password": "password2"
        })
        # Check for successful redirect (default is 302 on success)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "registration/login.html")
        self.assertContains(response, "Your account is inactive. Please contact support.")
        # verify that user is authenticated
        self.assertFalse("_auth_user_id" in self.unauthenticated_client.session)

    @patch("accounts.views.send_ses_email.delay")
    def test_signup_success_redirects(self, send_email_pch):
        response = self.unauthenticated_client.post(reverse("signup"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "strongpassword123",
            "password2": "strongpassword123"
        })
        # Assuming successful signup redirects (e.g., to login page or activation notice)
        self.assertEqual(response.status_code, 302)

        success_url = reverse("login")
        self.assertEqual(response.url, success_url)

        # Confirm user was created in DB
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.username, "newuser")
        self.assertFalse(user.is_active)

        domain = "testserver"  # Django test client default

        send_email_pch.assert_called()

        # Get arguments the function was called with
        args, kwargs = send_email_pch.call_args

        self.assertEqual(kwargs["to_email"], [user.email])
        self.assertEqual(kwargs["from_email"], settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(kwargs["subject"], "Activate Your Account")

        # Check that the UID and token are in the email body
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)

        # Optional: Just check the email contains expected patterns
        self.assertIn(f"/accounts/activate/{uid}/", kwargs["body_text"])
        self.assertIn(f"/accounts/activate/{uid}", kwargs["body_html"])
        self.assertIn("Please confirm your registration by clicking the link below", kwargs["body_html"])



    @patch("accounts.views.send_ses_email.delay")
    def test_signup_invalid_password_mismatch(self, send_email_pch):
        response = self.client.post(reverse("signup"), {
            "username": "user2",
            "email": "user2@example.com",
            "password1": "password123",
            "password2": "different123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,"The two password fields didn’t match.")

        self.assertFalse(User.objects.filter(username="user2").exists())
        self.assertEqual(response.template_name[0], "registration/signup.html")
        send_email_pch.assert_not_called()

    @patch("accounts.views.send_ses_email.delay")
    def test_signup_duplicate_username(self, send_email_pch):
        response = self.client.post(reverse("signup"), {
            "username": "testuser",
            "email": "new@example.com",
            "password1": "somepass123",
            "password2": "somepass123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")
        send_email_pch.assert_not_called()

    @patch("accounts.views.send_ses_email.delay")
    def test_signup_duplicate_email(self, send_email_pch):
        response = self.client.post(reverse("signup"), {
            "username": "testuserooooooo",
            "email": "testuser@gmail.com",
            "password1": "somepass123dgdgdgdg",
            "password2": "somepass123dgdgdgdg"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,"A user with that email already exists.")
        send_email_pch.assert_not_called()

    @patch("accounts.views.send_ses_email.delay")
    def test_resend_activation_success_redirects(self, send_email_pch):
        response = self.unauthenticated_client.post(reverse("resend_activation"), {
            "email": "inactive_user@gmail.com"
        })
        # Assuming successful signup redirects (e.g., to login page or activation notice)
        self.assertEqual(response.status_code, 302)

        success_url = reverse("login")
        self.assertEqual(response.url, success_url)

        domain = "testserver"  # Django test client default

        send_email_pch.assert_called()

        # Get arguments the function was called with
        args, kwargs = send_email_pch.call_args

        self.assertEqual(kwargs["to_email"], [AccountsTestCase.inactive_user.email])
        self.assertEqual(kwargs["from_email"], settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(kwargs["subject"], "Activate Your Account")

        # Check that the UID and token are in the email body
        uid = urlsafe_base64_encode(force_bytes(AccountsTestCase.inactive_user.pk))
        token = account_activation_token.make_token(AccountsTestCase.inactive_user)

        # Optional: Just check the email contains expected patterns
        self.assertIn(f"/accounts/activate/{uid}/", kwargs["body_text"])
        self.assertIn(f"/accounts/activate/{uid}", kwargs["body_html"])
        self.assertIn("Please confirm your registration by clicking the link below", kwargs["body_html"])

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "A new activation link has been sent to your email." for m in messages))

    @patch("accounts.views.send_ses_email.delay")
    def test_resend_activation_user_active(self, send_email_pch):
        response = self.unauthenticated_client.post(reverse("resend_activation"), {
            "email": "testuser@gmail.com"
        })
        # Assuming successful signup redirects (e.g., to login page or activation notice)
        self.assertEqual(response.status_code, 302)
        success_url = reverse("login")
        self.assertEqual(response.url, success_url)
        domain = "testserver"  # Django test client default
        send_email_pch.assert_not_called()
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "This account is already active." for m in messages))

    @patch("accounts.views.send_ses_email.delay")
    def test_resend_activation_user_not_exist(self, send_email_pch):
        response = self.unauthenticated_client.post(reverse("resend_activation"), {
            "email": "newuser@gmail.com"
        })
        # Assuming successful signup redirects (e.g., to login page or activation notice)
        self.assertEqual(response.status_code, 302)
        success_url = reverse("login")
        self.assertEqual(response.url, success_url)
        domain = "testserver"  # Django test client default
        send_email_pch.assert_not_called()
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "No account found with that email address." for m in messages))

    def test_valid_activation_token(self):
        """Test successful activation of user account"""
        user_obj = AccountsTestCase.inactive_user
        self.assertFalse(user_obj.is_active)
        uid = urlsafe_base64_encode(force_bytes(user_obj.pk))
        token = account_activation_token.make_token(user_obj)
        response = self.client.get(reverse('activate', kwargs={'uidb64': uid, 'token': token}))
        user_obj.refresh_from_db()
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(user_obj.is_active)

    def test_invalid_token(self):
        """Test activation with invalid token fails"""
        user_obj = AccountsTestCase.inactive_user
        self.assertFalse(user_obj.is_active)
        uid = urlsafe_base64_encode(force_bytes(user_obj.pk))
        response = self.client.get(reverse('activate', kwargs={'uidb64': uid, 'token': 'invalid-token'}))
        user_obj.refresh_from_db()
        self.assertFalse(user_obj.is_active)
        self.assertTemplateUsed(response, 'registration/account_activation_invalid.html')

    def test_invalid_uid(self):
        """Test activation with invalid uid fails gracefully"""
        user_obj = AccountsTestCase.inactive_user
        invalid_uid = urlsafe_base64_encode(force_bytes(9999))  # ID that doesn't exist
        token = account_activation_token.make_token(user_obj)
        response = self.client.get(reverse('activate', kwargs={'uidb64': invalid_uid, 'token': token}))
        self.assertTemplateUsed(response, 'registration/account_activation_invalid.html')

    def test_malformed_uid(self):
        """Test activation with completely malformed uid string"""
        user_obj = AccountsTestCase.inactive_user
        token = account_activation_token.make_token(user_obj)
        response = self.client.get(reverse('activate', kwargs={'uidb64': 'not-a-valid-uid', 'token': token}))
        self.assertTemplateUsed(response, 'registration/account_activation_invalid.html')

    @patch('accounts.utils.settings')
    @patch('accounts.utils.boto3.client')
    def test_ses_client_production_environment_uses_default_credentials(self, mock_boto_client, mock_settings):
        mock_settings.DJANGO_ENV = "PRODUCTION"
        mock_settings.AWS_REGION = "us-east-1"

        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        client = get_ses_client()
        mock_boto_client.assert_called_once_with('ses', region_name="us-east-1")
        self.assertEqual(client, mock_client_instance)

    @patch('accounts.utils.settings')
    @patch('accounts.utils.boto3.client')
    def test_ses_client_development_environment_uses_explicit_credentials(self, mock_boto_client, mock_settings):
        mock_settings.DJANGO_ENV = "DEVELOPMENT"
        mock_settings.AWS_REGION = "us-west-2"
        mock_settings.AWS_ACCESS_KEY = "FAKEKEY"
        mock_settings.AWS_SECRET_ACCESS_KEY = "FAKESECRET"

        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        client = get_ses_client()
        mock_boto_client.assert_called_once_with(
            'ses',
            aws_access_key_id="FAKEKEY",
            aws_secret_access_key="FAKESECRET",
            region_name="us-west-2"
        )
        self.assertEqual(client, mock_client_instance)

    @patch('accounts.utils.settings')
    @patch('accounts.utils.boto3.client', side_effect=Exception("SES failure"))
    def test_ses_client_returns_none_on_exception(self, mock_boto_client, mock_settings):
        mock_settings.DJANGO_ENV = "DEVELOPMENT"
        mock_settings.AWS_REGION = "eu-west-1"
        mock_settings.AWS_ACCESS_KEY = "INVALID"
        mock_settings.AWS_SECRET_ACCESS_KEY = "INVALID"

        client = get_ses_client()
        self.assertIsNone(client)


class CustomBackendTest(TestCase):
    def setUp(self):
        self.backend = CustomBackend()
        self.backend_user = BackendUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="securepass123"
        )

        self.inactive_user = BackendUser.objects.create_user(username="testuser2", email="test_yser_2@example.com",
                                                             password="kkkksskss")
        self.inactive_user.is_active = False
        self.inactive_user.save()

    def test_authenticate_with_username_success(self):
        authenticated_user = self.backend.authenticate(
            request=None, username="testuser", password="securepass123"
        )
        self.assertEqual(authenticated_user, self.backend_user)

    def test_authenticate_with_email_success(self):
        authenticated_user = self.backend.authenticate(
            request=None, username="test@example.com", password="securepass123"
        )
        self.assertEqual(authenticated_user, self.backend_user)

    def test_authenticate_with_wrong_password(self):
        authenticated_user = self.backend.authenticate(
            request=None, username="testuser", password="wrongpassword"
        )
        self.assertIsNone(authenticated_user)

    def test_authenticate_with_invalid_username_or_email(self):
        authenticated_user = self.backend.authenticate(
            request=None, username="doesnotexist", password="whatever"
        )
        self.assertIsNone(authenticated_user)

    def test_authenticate_inactive_user_does_not_allow_login(self):

        inactive_authenticated_user = self.backend.authenticate(
            request=None, username="test_yser_2@example.com", password="kkkksskss"
        )
        self.assertEqual(inactive_authenticated_user, self.inactive_user)
        self.assertFalse(inactive_authenticated_user.is_active)

    def test_get_user_valid(self):
        user = self.backend.get_user(self.backend_user.id)
        self.assertEqual(user, self.backend_user)

    def test_get_user_invalid(self):
        user = self.backend.get_user(9999)  # non-existent user ID
        self.assertIsNone(user)

    def test_get_user_inactive(self):
        user = self.backend.get_user(self.inactive_user.id)
        self.assertIsNone(user)
