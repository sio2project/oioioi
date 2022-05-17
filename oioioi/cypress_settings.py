# pylint: disable=wildcard-import
from settings import *

# Enable optional modules.
INSTALLED_APPS = (
    'oioioi.teachers',
    'oioioi.ipdnsauth',
    'oioioi.zeus',
    'oioioi.oireports',
    'oioioi.oisubmit',
    'oioioi.complaints',
    'oioioi.exportszu',
    'oioioi.similarsubmits',
    'oioioi.disqualification',
    'oioioi.submitservice',
    'oioioi.amppz',
    'oioioi.teams',
    'oioioi.pa',
    'oioioi.notifications',
    'oioioi.mailsubmit',
    'oioioi.portals',
    'oioioi.newsfeed',
    'oioioi.simpleui',
    'oioioi.livedata',
) + INSTALLED_APPS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'ATOMIC_REQUESTS': True,
    }
}

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'oioioi.portals.processors.portal_processor',
]

AUTHENTICATION_BACKENDS += (
    'oioioi.base.tests.IgnorePasswordAuthBackend',
    'oioioi.teachers.auth.TeacherAuthBackend',
)

MIDDLEWARE += ('oioioi.base.tests.FakeTimeMiddleware',)

TESTS = True
MOCK_RANKINGSD = True

SECRET_KEY = 'no_secret'
OISUBMIT_MAGICKEY = 'abcdef'
USE_UNSAFE_EXEC = True
USE_UNSAFE_CHECKER = True

COMPLAINTS_EMAIL = 'dummy@example.com'
COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

WARN_ABOUT_REPEATED_SUBMISSION = False

PROBLEM_SOURCES += ('oioioi.zeus.problem_sources.ZeusProblemSource',)

ZEUS_INSTANCES = {
    'dummy': ('__use_object__', 'oioioi.zeus.tests.ZeusDummyServer', ('', '', '')),
}

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Do not print migrations DEBUG to console.
LOGGING['loggers']['django.db.backends.schema'] = {
    'handlers': ['console'],
    'level': 'INFO',
}

CAPTCHA_TEST_MODE = True
DEBUG = True
