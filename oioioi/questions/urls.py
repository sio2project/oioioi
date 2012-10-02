from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.questions.views',
    url(r'^messages$', 'messages_view', name='contest_messages'),
    url(r'^messages/(?P<message_id>\d+)$', 'message_view', name='message'),
    url(r'^messages/(?P<message_id>\d+)/reply$', 'add_reply_view',
        name='message_reply'),
    url(r'^messages/add$', 'add_contest_message_view',
        name='add_contest_message'),
)

urlpatterns = patterns('oioioi.contests.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
