from django.conf import settings
from django.core.management.commands import migrate
from django.db import connection

import os

GITHUB_LINK = "https://github.com/sio2project/oioioi" \
        "#upgrading-from-an-old-version"


class Command(migrate.Command):

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        split = db['ENGINE'].split('.')
        if (not getattr(settings, 'TESTS', False)
                and len(split) >= 4 and split[3] == 'sqlite3'
                and not os.path.isabs(db['NAME'])):
            self.stderr.write("Since you are using sqlite3 it is important"
                              " to provide the absolute database file path\n")
            self.stderr.write("To be honest - we recommend not to use SQLite3 "
                              "in production\n")
            return

        tables = connection.introspection.table_names()
        if 'south_migrationhistory' in tables:
            query = "SELECT * from south_migrationhistory " \
                    "WHERE migration = '0002_final_south_migration'"
            with connection.cursor() as cursor:
                cursor.execute(query)
                if cursor.rowcount == 0:
                    self.stderr.write("It looks like you're upgrading from "
                                      "an old version of OIOIOI that was "
                                      "based on version 1.5 or 1.6 of the "
                                      "Django framework. You'll have to make "
                                      "an extra step before syncing your "
                                      "database. Consult %s for "
                                      "instructions." % GITHUB_LINK)

                    return
        super(Command, self).handle(*args, **options)
