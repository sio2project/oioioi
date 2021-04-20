from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.conf.urls import include, url
from rest_framework.documentation import include_docs_urls
from two_factor.urls import urlpatterns as tf_urls

from oioioi.base import admin, api, views
from oioioi.base.main_page import main_page_view

app_name = 'base'

if DJANGO_VERSION < (1, 11):
    # in django_two_factor_auth 1.7 urlpatterns become a tuple
    # and presumably break things
    assert type(tf_urls) != tuple

urlpatterns = [
    url(r'', include(tf_urls)),
    url(r'^force_error/$', views.force_error_view, name='force_error'),
    url(
        r'^force_permission_denied/$',
        views.force_permission_denied_view,
        name='force_permission_denied',
    ),
    url(r'^edit_profile/$', views.edit_profile_view, name='edit_profile'),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^translate/$', views.translate_view, name='translate'),
    url(r'^login/$', views.login_view, name='login'),
    url(r'^delete_account/$', views.delete_account_view, name='delete_account'),
    url(r'^generate_key/$', views.generate_key_view, name='generate_key'),
    # don't include without appropriate patching! admincdocs provides its own
    # login view which can be used to bypass 2FA.
    #   url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/logout/$', views.logout_view),
    url(r'^admin/', admin.site.urls),
]

urlpatterns += [
    url(r'^$', main_page_view, name='index'),
]

noncontest_patterns = []

if settings.USE_API:
    urlpatterns += [
        url(r'^api/token', api.api_token, name='api_token'),
        url(r'^api/regenerate_token', api.regenerate_token, name='api_regenerate_key'),
    ]
    noncontest_patterns += [
        # the c prefix doesn't make sense for non contest related endpoints as
        # well as for the documentation which anyway does not require authorization
        url(r'^api/docs/', include_docs_urls(title='OIOIOI API'), name='api_docs'),
        url(r'^api/ping', api.ping),
        url(r'^api/auth_ping', api.auth_ping),
    ]
