from django.conf.urls import include, url

from oioioi.base import admin, views
from oioioi.base.main_page import main_page_view

urlpatterns = [
    url(r'', include('two_factor.urls', 'two_factor')),
    url(r'^force_error/$', views.force_error_view, name='force_error'),
    url(r'^force_permission_denied/$', views.force_permission_denied_view,
        name='force_permission_denied'),
    url(r'^edit_profile/$', views.edit_profile_view, name='edit_profile'),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^translate/$', views.translate_view, name='translate'),
    url(r'^login/$', views.login_view, name='login'),
    url(r'^delete_account/$', views.delete_account_view,
        name='delete_account'),
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
