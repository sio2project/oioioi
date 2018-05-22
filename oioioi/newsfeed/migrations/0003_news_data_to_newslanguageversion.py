# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def move_news_data_to_newslanguageversion(apps, schema_editor):
    News = apps.get_model('newsfeed', 'News')
    NewsLanguageVersion = apps.get_model('newsfeed', 'NewsLanguageVersion')

    for news in News.objects.all():
        news_content = NewsLanguageVersion(news=news, language=settings.LANGUAGE_CODE,
                                     title=news.title, content=news.content)
        news_content.save()


def reverse_news_data_migration(apps, schema_editor):
    News = apps.get_model('newsfeed', 'News')
    NewsLanguageVersion = apps.get_model('newsfeed', 'NewsLanguageVersion')

    for news in News.objects.all():
        try:
            default_news_content = news.versions.get(
                language=settings.LANGUAGE_CODE)
        except NewsLanguageVersion.DoesNotExist:
            default_news_content = news.versions.first()

        if default_news_content is not None:
            news.title = default_news_content.title
            news.content = default_news_content.content
            news.save()


class Migration(migrations.Migration):

    dependencies = [
        ('newsfeed', '0002_newslanguageversion'),
    ]

    operations = [
        migrations.RunPython(move_news_data_to_newslanguageversion,
                             reverse_news_data_migration)
    ]
