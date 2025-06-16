from django.urls import path
from django.urls import re_path

from oioioi.questions import views

app_name = 'questions'

contest_patterns = [
    path('questions/', views.messages_view, name='contest_messages'),
    path('questions/all/', views.all_messages_view, name='contest_all_messages'),
    path('questions/<int:message_id>/', views.message_view, name='message'),
    path(
        'questions/<int:message_id>/visit',
        views.message_visit_view,
        name='message_visit',
    ),
    path(
        'questions/<int:message_id>/mark_read',
        views.toggle_question_read,
        {'read': True},
        name='mark_question_read',
    ),
    path(
        'questions/<int:message_id>/mark_unread',
        views.toggle_question_read,
        {'read': False},
        name='mark_question_unread',
    ),
    path(
        'questions/add/', views.add_contest_message_view, name='add_contest_message'
    ),
    path('questions/subscription/', views.subscription, name='subscription'),
    path(
        'questions/get_messages_authors/',
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
    path(
        'questions/check_new_messages/<int:topic_id>/',
        views.check_new_messages_view,
        name='check_new_messages',
    ),
    path(
        'questions_message/',
        views.news_edit_view,
        name='edit_question_news_message',
    ),
    path(
        'questions/add_message/',
        views.add_edit_message_view,
        name='edit_add_question_message',
    ),
]
