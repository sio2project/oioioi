import logging

from nose.plugins import Plugin


class DisableSouthDebugMessages(Plugin):
    def configure(self, options, conf):
        super(DisableSouthDebugMessages, self).configure(options, conf)
        logging.getLogger('south').setLevel(logging.INFO)
