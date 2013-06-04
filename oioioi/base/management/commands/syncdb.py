from django.conf import settings

from south.management.commands import syncdb

import os


class Command(syncdb.Command):

    def handle_noargs(self, **options):
        db = settings.DATABASES['default']
        split = db['ENGINE'].split('.')
        if (len(split) >= 4 and split[3] == 'sqlite3'
            and not os.path.isabs(db['NAME'])):
            self.stderr.write("Since you are using sqlite3 it is important"
                              " to provide the absolute database file path\n")
            self.stderr.write("To be honest - we recommend not to use SQLite3 "
                              "in production\n")
        else:
            super(Command, self).handle_noargs(**options)
