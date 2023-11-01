from django.urls import re_path

from oioioi.questions import views

app_name = 'questions'

contest_patterns = [
    re_path(r'^questions/$', views.messages_view, name='contest_messages'),
    re_path(r'^questions/all/$', views.all_messages_view, name='contest_all_messages'),
    re_path(r'^questions/(?P<message_id>\d+)/$', views.message_view, name='message'),
    re_path(
        r'^questions/(?P<message_id>\d+)/visit$',
        views.message_visit_view,
        name='message_visit',
    ),
    re_path(
        r'^questions/(?P<message_id>\d+)/mark_read$',
        views.toggle_question_read,
        {'read': True},
        name='mark_question_read',
    ),
    re_path(
        r'^questions/(?P<message_id>\d+)/mark_unread$',
        views.toggle_question_read,
        {'read': False},
        name='mark_question_unread',
    ),
    re_path(
        r'^questions/add/$', views.add_contest_message_view, name='add_contest_message'
    ),
    re_path(r'^questions/subscription/$', views.subscription, name='subscription'),
    re_path(
        r'^questions/get_messages_authors/$',
        views.get_messages_authors_view,
        name='get_messages_authors',
    ),
    re_path(
        r'^questions/get_reply_templates/',
        views.get_reply_templates_view,
        name='get_reply_templates',
    ),
    re_path(
        r'^questions/increment_template_usage/(?:(?P<template_id>\d+)/)?$',
        views.increment_template_usage_view,
        name='increment_template_usage',
    ),
    re_path(
        r'^questions/check_new_messages/(?P<topic_id>\d+)/$',
        views.check_new_messages_view,
        name='check_new_messages',
    ),
    re_path(
        r'^questions_message/$',
        views.news_edit_view,
        name='edit_question_news_message',
    ),
    re_path(
        r'^questions/add_message/$',
        views.add_edit_message_view,
        name='edit_add_question_message',
    ),
]
