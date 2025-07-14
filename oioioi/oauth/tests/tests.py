import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

from oioioi.base.tests import TestCase

User = get_user_model()


@override_settings(
    OAUTH2_PROVIDER={
        "SCOPES": {"read": "Read access", "write": "Write access"},
        "ALLOWED_GRANT_TYPES": ["password", "authorization_code", "client_credentials", "refresh_token"],
    }
)
class PasswordGrantTestCase(TestCase):
    fixtures = ["test_users"]

    def setUp(self):
        # For this test, we need to explicitly create a password-grant-based app
        # Since secrets are hashed we will store their plaintext as members
        self.user_pwd = "password"
        self.user = User.objects.create_user("oauth_test_user", "test@example.com", self.user_pwd)

        self.app_secret = "test-client-secret"
        self.application = Application.objects.create(
            name="Password Grant Test App",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
            client_id="test-client-id",
            client_secret=self.app_secret,
            redirect_uris="",
        )

        # Create an access token for reference
        self.access_token = AccessToken.objects.create(
            user=self.user, application=self.application, token="test_token", expires=timezone.now() + timedelta(days=1), scope="read write"
        )

        self.api_client = APIClient()

    # Test a token created without a grant for reference
    def test_protected_endpoint_with_token(self):
        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token.token}")
        response = self.api_client.get("/api/auth_ping")
        self.assertEqual(response.status_code, 200)

        self.api_client.credentials()
        response = self.api_client.get("/api/auth_ping")
        self.assertEqual(response.status_code, 403)

    def test_token_flow(self):
        token_url = reverse("oauth2_provider:token")

        response = self.client.post(
            token_url,
            {
                "grant_type": Application.GRANT_PASSWORD,
                "username": self.user.username,
                "password": self.user_pwd,
                "client_id": self.application.client_id,
                "client_secret": self.app_secret,
            },
        )

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode("utf-8"))
        self.assertIn("access_token", content)
        self.assertIn("token_type", content)
        self.assertEqual(content["token_type"], "Bearer")

        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {content['access_token']}")
        response = self.api_client.get("/api/auth_ping")
        self.assertEqual(response.status_code, 200)

        self.api_client.credentials()
        response = self.api_client.get("/api/auth_ping")
        self.assertEqual(response.status_code, 403)
