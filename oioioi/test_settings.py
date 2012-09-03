from oioioi.default_settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

AUTHENTICATION_BACKENDS = (
    'oioioi.base.tests.IgnorePasswordAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

TESTS = True

SECRET_KEY = 'no_secret'
COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = ()
CELERY_ALWAYS_EAGER = True
SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.LocalBackend'
FILETRACKER_CLIENT_FACTORY = 'filetracker.dummy.DummyClient'
USE_UNSAFE_EXEC = True
USE_LOCAL_COMPILERS = True
