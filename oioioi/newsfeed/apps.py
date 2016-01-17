from django.apps import AppConfig

from oioioi.portals.widgets import register_widget
from oioioi.newsfeed.widgets import NewsWidget, NewsfeedWidget


class NewsfeedAppConfig(AppConfig):
    name = 'oioioi.newsfeed'

    def ready(self):
        register_widget(NewsWidget())
        register_widget(NewsfeedWidget())
