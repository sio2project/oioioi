from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.participants.views',
    url(r'^register/$', 'registration_view', name='participants_register'),
    url(r'^unregister/$', 'unregistration_view',
        name='participants_unregister'),
)

urlpatterns = patterns('oioioi.participants.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
