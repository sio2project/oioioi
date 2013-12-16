from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.questions.views',
    url(r'^questions/$', 'messages_view', name='contest_messages'),
    url(r'^questions/(?P<message_id>\d+)/$', 'message_view', name='message'),
    url(r'^questions/add/$', 'add_contest_message_view',
        name='add_contest_message'),
    url(r'^questions/get_messages_authors/', 'get_messages_authors_view',
        name='get_messages_authors'),
    url(r'^questions/get_reply_templates/', 'get_reply_templates_view',
        name='get_reply_templates'),
    url(r'^questions/increment_template_usage/(?:(?P<template_id>\d+)/)?$',
        'increment_template_usage_view', name='increment_template_usage'),
)

urlpatterns = patterns('oioioi.contests.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
