from django.utils.translation import gettext_lazy as _
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.exceptions import AuthenticationFailed


class ActiveUserOAuth2Authentication(OAuth2Authentication):
    """OAuth2 authentication that refuses tokens of inactive users, as DRF's ``TokenAuthentication`` does."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and result[0] is not None and not result[0].is_active:
            raise AuthenticationFailed(_("User inactive or deleted."))
        return result
