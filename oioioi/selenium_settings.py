# pylint: disable=wildcard-import
from oioioi.default_settings import *

TIME_ZONE = 'UTC'

SITE_ID = 1

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
    'oioioi.exportszu',
    'oioioi.similarsubmits',
    'oioioi.disqualification',
    'oioioi.confirmations',
    'oioioi.ctimes',
    'oioioi.acm',
    'oioioi.suspendjudge',
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
    'oioioi.mailsubmit',
    'oioioi.globalmessage',
    'oioioi.portals',
    'oioioi.newsfeed',
    'oioioi.simpleui',
    'oioioi.livedata',
) + INSTALLED_APPS

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'oioioi.contestlogo.processors.logo_processor',
    'oioioi.contestlogo.processors.icon_processor',
    'oioioi.globalmessage.processors.global_message_processor',
    'oioioi.portals.processors.portal_processor',
]

AUTHENTICATION_BACKENDS += (
    'oioioi.base.tests.IgnorePasswordAuthBackend',
    'oioioi.teachers.auth.TeacherAuthBackend',
)

MIDDLEWARE_CLASSES += (
    'oioioi.base.tests.FakeTimeMiddleware',
)

TESTS = True
MOCK_RANKINGSD = True

SECRET_KEY = 'no_secret'
OISUBMIT_MAGICKEY = 'abcdef'
USE_UNSAFE_EXEC = True
USE_UNSAFE_CHECKER = True

AVAILABLE_COMPILERS = {
    'C': {
        'system-gcc': {'display_name': 'system gcc'}
    },
    'C++': {
        'system-g++': {'display_name': 'system g++'}
    },
    'Pascal': {
        'system-fpc': {'display_name': 'system fpc'}
    },
    'Java': {
        'system-java': {'display_name': 'system java'}
    },
    'Python': {
        'system-python': {'display_name': 'system python'}
    }
}

DEFAULT_COMPILERS = {'C': 'system-gcc', 'C++': 'system-g++',
                     'Pascal': 'system-fpc', 'Java': 'system-java',
                     'Python': 'system-python'}

USE_SINOLPACK_MAKEFILES = True


COMPLAINTS_EMAIL = 'dummy@example.com'
COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

WARN_ABOUT_REPEATED_SUBMISSION = False

BALLOON_ACCESS_COOKIE_EXPIRES_DAYS = 7

PROBLEM_SOURCES += (
    'oioioi.zeus.problem_sources.ZeusProblemSource',
)

ZEUS_INSTANCES = {
    'dummy': ('__use_object__',
              'oioioi.zeus.tests.ZeusDummyServer', ('', '', '')),
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

CONFIG_VERSION = INSTALLATION_CONFIG_VERSION

# Do not print migrations DEBUG to console.
LOGGING['loggers']['django.db.backends.schema'] = {
    'handlers': ['console'],
    'level': 'INFO',
}