import logging

from nose.plugins import Plugin

from django.core.cache import cache


class DisableSouthDebugMessages(Plugin):
    def configure(self, options, conf):
        super(DisableSouthDebugMessages, self).configure(options, conf)
        logging.getLogger('south').setLevel(logging.INFO)


class ClearCache(Plugin):
    def startTest(self, test):
        cache.clear()
