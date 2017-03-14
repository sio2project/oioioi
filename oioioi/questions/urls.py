from django.conf.urls import url

from oioioi.questions import views


contest_patterns = [
    url(r'^questions/$', views.messages_view, name='contest_messages'),
    url(r'^questions/all/$', views.all_messages_view,
        name='contest_all_messages'),
    url(r'^questions/(?P<message_id>\d+)/$', views.message_view,
        name='message'),
    url(r'^questions/(?P<message_id>\d+)/visit$', views.message_visit_view,
        name='message_visit'),
    url(r'^questions/add/$', views.add_contest_message_view,
        name='add_contest_message'),
    url(r'^questions/subscription/$', views.subscription,
        name='subscription'),
    url(r'^questions/get_messages_authors/$', views.get_messages_authors_view,
        name='get_messages_authors'),
    url(r'^questions/get_reply_templates/', views.get_reply_templates_view,
        name='get_reply_templates'),
    url(r'^questions/increment_template_usage/(?:(?P<template_id>\d+)/)?$',
        views.increment_template_usage_view, name='increment_template_usage'),
    url(r'^questions/check_new_messages/(?P<topic_id>\d+)/$',
        views.check_new_messages_view, name='check_new_messages'),
]
