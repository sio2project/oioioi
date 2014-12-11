from nose.plugins import Plugin

from django.core.cache import cache


class ClearCache(Plugin):
    def startTest(self, test):
        cache.clear()
