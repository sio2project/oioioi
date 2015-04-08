from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.base.views',
    url(r'^$', 'index_view', name='index'),
    url(r'^force_error/$', 'force_error_view', name='force_error'),
    url(r'^force_permission_denied/$', 'force_permission_denied_view',
        name='force_permission_denied'),
    url(r'^edit_profile/$', 'edit_profile_view', name='edit_profile'),
    url(r'^logout/$', 'logout_view', name='logout'),
    url(r'^translate/$', 'translate_view', name='translate'),
    url(r'^admin/logout/$', 'logout_view'),
    url(r'^login/$', 'login_view', name='login'),
    url(r'^delete_account/$', 'delete_account_view', name='delete_account'),
    url(r'^generate_key/$', 'generate_key_view', name='generate_key'),
)
