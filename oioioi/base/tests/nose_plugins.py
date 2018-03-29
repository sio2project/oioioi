from django.core.cache import cache
from nose.plugins import Plugin


class ClearCache(Plugin):
    def startTest(self, test):
        cache.clear()
