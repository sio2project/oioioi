# pylint: disable=wildcard-import
from oioioi.default_settings import *

TIME_ZONE = 'UTC'

ADMINS = (
    ('Test admin', 'admin@example.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'ATOMIC_REQUESTS': True,
    }
}

# Enable optional modules.
INSTALLED_APPS = (
    'oioioi.contestlogo',
    'oioioi.teachers',
    'oioioi.ipdnsauth',
    'oioioi.participants',
    'oioioi.oi',
    'oioioi.printing',
    'oioioi.zeus',
    'oioioi.testrun',
    'oioioi.scoresreveal',
    'oioioi.oireports',
    'oioioi.oisubmit',
    'oioioi.complaints',
    'oioioi.contestexcl',
    'oioioi.forum',
    'oioioi.disqualification',
    'oioioi.confirmations',
    'oioioi.ctimes',
    'oioioi.acm',
    'oioioi.suspendjudge',
    'oioioi.submitsqueue',
    'oioioi.submitservice',
    'oioioi.timeline',
    'oioioi.statistics',
    'oioioi.amppz',
    'oioioi.balloons',
    'oioioi.publicsolutions',
    'oioioi.testspackages',
    'oioioi.teams',
    'oioioi.pa',
    'oioioi.notifications',
    'oioioi.prizes',
    'oioioi.mailsubmit',
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

NOSE_PLUGINS = [
    'oioioi.base.tests.nose_plugins.ClearCache',
]

SECRET_KEY = 'no_secret'
OISUBMIT_MAGICKEY = 'abcdef'
COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = ()
CELERY_ALWAYS_EAGER = True
SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.LocalBackend'
FILETRACKER_CLIENT_FACTORY = 'filetracker.dummy.DummyClient'
USE_UNSAFE_EXEC = True
USE_LOCAL_COMPILERS = True

USE_SINOLPACK_MAKEFILES = True


COMPLAINTS_EMAIL = 'dummy@example.com'
COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

WARN_ABOUT_REPEATED_SUBMISSION = False

BALLOON_ACCESS_COOKIE_EXPIRES_DAYS = 7

PROBLEM_SOURCES += (
    'oioioi.zeus.problem_sources.ZeusProblemSource',
)

ZEUS_INSTANCES = {
    'zeus_correct': ('__use_object__',
                     'oioioi.zeus.tests.ZeusCorrectServer', ''),
    'zeus_incorrect': ('__use_object__',
                       'oioioi.zeus.tests.ZeusIncorrectServer', ''),
    'dummy': ('__use_object__',
              'oioioi.zeus.tests.ZeusDummyServer', ''),
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

CONFIG_VERSION = INSTALLATION_CONFIG_VERSION

STATIC_ROOT = ''
