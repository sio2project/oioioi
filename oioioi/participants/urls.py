from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.participants.views',
    url(r'^register/$', 'registration_view', name='participants_register'),
    url(r'^unregister/$', 'unregistration_view',
        name='participants_unregister'),
    url(r'^participants_data/$', 'participants_data', name='participants_data'),
    url(r'^participants_data_csv/$', 'participants_data_csv',
        name='participants_data_csv'),
)

urlpatterns = patterns('oioioi.participants.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
