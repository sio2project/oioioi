# pylint: disable=wildcard-import
import django

from oioioi.default_settings import *

TIME_ZONE = 'UTC'

SITE_ID = 1

ADMINS = (('Test admin', 'admin@example.com'),)

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
    'oioioi.szkopul',
    'oioioi.complaints',
    'oioioi.contestexcl',
    'oioioi.forum',
    'oioioi.exportszu',
    'oioioi.plagiarism',
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
    'oioioi.usergroups',
    'oioioi.problemsharing',
    'oioioi.usercontests',
    'oioioi.mp',
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
    'oioioi.usercontests.auth.UserContestAuthBackend',
)

MIDDLEWARE += ('oioioi.base.tests.FakeTimeMiddleware',)

TESTS = True
MOCK_RANKINGSD = True

SECRET_KEY = 'no_secret'
OISUBMIT_MAGICKEY = 'abcdef'
COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = ()
CELERY_ALWAYS_EAGER = True
SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.LocalBackend'
FILETRACKER_CLIENT_FACTORY = 'filetracker.client.dummy.DummyClient'
FILETRACKER_URL = None
USE_UNSAFE_EXEC = True
USE_UNSAFE_CHECKER = True

AVAILABLE_COMPILERS = SYSTEM_COMPILERS
DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS

USE_SINOLPACK_MAKEFILES = True
SINOLPACK_RESTRICT_HTML = False


COMPLAINTS_EMAIL = 'dummy@example.com'
COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

WARN_ABOUT_REPEATED_SUBMISSION = False

# Experimental according to default_settings.py
USE_ACE_EDITOR = True

PROBLEM_SOURCES += ('oioioi.zeus.problem_sources.ZeusProblemSource',)

ZEUS_INSTANCES = {
    'dummy': ('__use_object__', 'oioioi.zeus.tests.ZeusDummyServer', ('', '', '')),
}

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

CONFIG_VERSION = INSTALLATION_CONFIG_VERSION

STATIC_ROOT = ''

# Do not print migrations DEBUG to console.
LOGGING['loggers']['django.db.backends.schema'] = {
    'handlers': ['console'],
    'level': 'INFO',
}
