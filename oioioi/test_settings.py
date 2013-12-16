# pylint: disable-msg=W0401
from oioioi.default_settings import *

TIME_ZONE = 'UTC'

ADMINS = (
    ('Test admin', 'admin@example.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# Enable optional modules.
INSTALLED_APPS = (
    'oioioi.contestlogo',
    'oioioi.teachers',
    'oioioi.dashboard',
    'oioioi.clock',
    'oioioi.ipdnsauth',
    'oioioi.participants',
    'oioioi.oi',
    'oioioi.printing',
    'oioioi.testrun',
    'oioioi.scoresreveal',
    'oioioi.oireports',
    'oioioi.oisubmit',
    'oioioi.complaints',
    'oioioi.contestexcl',
    'oioioi.forum',
    'oioioi.confirmations',
    'oioioi.ctimes',
    'oioioi.acm',
    'oioioi.submitsqueue',
    'oioioi.timeline',
    'oioioi.statistics',
    'oioioi.publicsolutions',
) + INSTALLED_APPS

TEMPLATE_CONTEXT_PROCESSORS += (
    'oioioi.contestlogo.processors.logo_processor',
    'oioioi.contestlogo.processors.icon_processor',
)

AUTHENTICATION_BACKENDS += (
    'oioioi.base.tests.IgnorePasswordAuthBackend',
    'oioioi.teachers.auth.TeacherAuthBackend',
)

MIDDLEWARE_CLASSES += (
    'oioioi.base.tests.FakeTimeMiddleware',
)

TESTS = True

SECRET_KEY = 'no_secret'
OISUBMIT_MAGICKEY = 'abcdef'
COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = ()
CELERY_ALWAYS_EAGER = True
SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.LocalBackend'
FILETRACKER_CLIENT_FACTORY = 'filetracker.dummy.DummyClient'
USE_UNSAFE_EXEC = True
USE_LOCAL_COMPILERS = True

COMPLAINTS_EMAIL = 'dummy@example.com'
COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

WARN_ABOUT_REPEATED_SUBMISSION = False
