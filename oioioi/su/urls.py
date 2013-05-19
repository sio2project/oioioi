from django.conf.urls import patterns, url


urlpatterns = patterns('oioioi.su.views',
    url(r'^su/$', 'su_view', name='su'),
    url(r'^get_suable_usernames/', 'get_suable_users_view',
            name='get_suable_users'),
    url(r'^su_reset/$', 'su_reset_view', name='su_reset'),
)
