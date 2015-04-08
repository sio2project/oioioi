from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.gamification.views',
    url(r'^profile/$', 'profile_view', name='view_current_profile'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/$', 'profile_view',
        name='view_profile')
)
