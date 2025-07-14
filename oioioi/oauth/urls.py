import oauth2_provider.views as oauth2_views
from django.conf import settings
from django.urls import include, re_path

from .middleware import (
    AdminApplicationDelete,
    AdminApplicationDetail,
    AdminApplicationList,
    AdminApplicationRegistration,
    AdminApplicationUpdate,
)

app_name = "oauth"

oauth2_endpoint_views = [
    re_path(r"^authorize/", oauth2_views.AuthorizationView.as_view(), name="authorize"),
    re_path(r"^token/", oauth2_views.TokenView.as_view(), name="token"),
    re_path(r"^revoke-token/", oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
]

if settings.DEBUG:
    # OAuth2 Application Management endpoints
    oauth2_endpoint_views += [
        re_path(r"^applications/register/", AdminApplicationRegistration.as_view(), name="register"),
        re_path(r"^applications/(?P<pk>\d+)/", AdminApplicationDetail.as_view(), name="detail"),
        re_path(r"^applications/(?P<pk>\d+)/delete/", AdminApplicationDelete.as_view(), name="delete"),
        re_path(r"^applications/(?P<pk>\d+)/update/", AdminApplicationUpdate.as_view(), name="update"),
        re_path(r"^applications/", AdminApplicationList.as_view(), name="list"),
    ]

    oauth2_endpoint_views += [
        re_path(r"^authorized-tokens/", oauth2_views.AuthorizedTokensListView.as_view(), name="authorized-token-list"),
        re_path(r"^authorized-tokens/<pk>/delete/", oauth2_views.AuthorizedTokenDeleteView.as_view(), name="authorized-token-delete"),
    ]

urlpatterns = [
    re_path(r"^o/", include((oauth2_endpoint_views, "oauth2_provider"), namespace="oauth2_provider")),
]
