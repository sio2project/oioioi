from django.conf.urls import patterns, url

noncontest_patterns = patterns('oioioi.notifications.views',
                               url(r'^notifications/authenticate/$',
                                   'notifications_authenticate_view',
                                   name='notifications_authenticate'),
                               )
