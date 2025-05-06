from django.conf import settings
from django.urls import path
from django.urls import include, re_path
from oioioi.base import admin, api, views
from oioioi.base.main_page import main_page_view
from rest_framework.documentation import include_docs_urls
from two_factor.urls import urlpatterns as tf_urls

app_name = 'base'

urlpatterns = [
    path('', include(tf_urls)),
    path('force_error/', views.force_error_view, name='force_error'),
    path(
        'force_permission_denied/',
        views.force_permission_denied_view,
        name='force_permission_denied',
    ),
    path('edit_profile/', views.edit_profile_view, name='edit_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('translate/', views.translate_view, name='translate'),
    path('login/', views.login_view, name='login'),
    path('delete_account/', views.delete_account_view, name='delete_account'),
    path('generate_key/', views.generate_key_view, name='generate_key'),
    # don't include without appropriate patching! admincdocs provides its own
    # login view which can be used to bypass 2FA.
    #   re_path(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/logout/', views.logout_view),
]

urlpatterns += [
    path('', main_page_view, name='index'),
]

noncontest_patterns = [
    # The contest versions are included by contests.admin.contest_site
    re_path(r'^admin/', admin.site.urls),
]

if settings.USE_API:
    urlpatterns += [
        re_path(r'^api/token', api.api_token, name='api_token'),
        re_path(r'^api/regenerate_token', api.regenerate_token, name='api_regenerate_key'),
    ]
    noncontest_patterns += [
        # the c prefix doesn't make sense for non contest related endpoints as
        # well as for the documentation which anyway does not require authorization
        re_path(r'^api/docs/', include_docs_urls(title='OIOIOI API'), name='api_docs'),
        re_path(r'^api/ping', api.ping),
        re_path(r'^api/auth_ping', api.auth_ping),
    ]
