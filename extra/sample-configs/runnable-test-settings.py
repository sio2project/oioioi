# pylint: disable=wildcard-import

import oioioi.default_settings
from oioioi.test_settings import *

DEBUG = True
COMPRESS_ENABLED = True
COMPRESS_PRECOMPILERS = oioioi.default_settings.COMPRESS_PRECOMPILERS
FILETRACKER_CLIENT_FACTORY = oioioi.default_settings.FILETRACKER_CLIENT_FACTORY
FILETRACKER_CACHE_ROOT = "/tmp/oioioi-filetracker-cache"
STATIC_ROOT = "/tmp/oioioi-static-root"

DATABASES = {
    "default": {
        "NAME": "/tmp/oioioi.sqlite3",
        "ENGINE": "django.db.backends.sqlite3",
        "ATOMIC_REQUESTS": True,
    }
}

#
# One-time setup:
#
# oioioi-create-config test-deployment
# cd test-deployment
# cp -f ../oioioi/extra/sample-configs/runnable-test-settings.py settings.py
# ./manage.py migrate
# ./manage.py collectstatic
#
# To import fixtures:
#
# ./manage.py loaddata ../oioioi/.../fixtures/test_foo.json
#
# To change user password:
#
# ./manage.py changepassword test_admin
#

#
# To workaround a bug, where sioworkers is not passed
# FILETRACKER_CACHE_ROOT, use this to start the website:
#
# FILETRACKER_URL=/tmp/oioioi-filetracker-cache ./manage.py runserver
#

#
# Then after you have set up objects using the web app,
# you can create new fixtures like this:
#
# ./manage.py dumpdata app1 app2 ... | json_pp > fixture.json
#
# e.g.
#
# ./manage.py dumpdata contests problems prorams | json_pp > fixture.json
#
# Then test again by deleting the database (/tmp/oioioi.sqlite3)
# and recreating it from all needed fixtures.
#
