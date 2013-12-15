# pylint: disable=W0401
# Wildcard import
import sys
if sys.version_info < (2, 6):
    raise RuntimeError("OIOIOI needs at least Python 2.6")

import os

os.environ.setdefault('CELERY_LOADER', 'oioioi.celery.loaders.OioioiLoader')
import djcelery
djcelery.setup_loader()

import oioioi

DEBUG = False
TEMPLATE_DEBUG = DEBUG
INTERNAL_IPS = ('127.0.0.1',)

# Site name displayed in the title
SITE_NAME = 'OIOIOI'

# Run uwsgi daemon. Shall be True, False or 'auto'.
# 'auto' means daemon will be run iff DEBUG is disabled.
UWSGI_ENABLED = 'auto'

UWSGI_USE_GEVENT = False

LANGUAGES = (
    ('en', 'English'),
    ('pl', 'Polish'),
)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'
LANGUAGE_COOKIE_NAME = 'lang'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LOCALE_PATHS = [
    os.path.join(os.path.dirname(oioioi.__file__), 'locale'),
    os.path.join(os.path.dirname(oioioi.__file__), 'locale-overrides'),
]

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

DATETIME_FORMAT = 'Y-m-d H:i:s'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = None

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'oioioi.su.processors.real_user',
    'oioioi.base.processors.base_url',
    'oioioi.base.processors.side_menus',
    'oioioi.base.processors.site_name',
    'oioioi.jotform.processors.jotform',
    'oioioi.contests.processors.register_current_contest',
    'oioioi.contests.processors.register_recent_contests',
    'oioioi.contestexcl.processors.register_contest_exclusive',
    'oioioi.problems.processors.dangling_problems_processor',
    'oioioi.questions.processors.navbar_tip_processor',
    'oioioi.analytics.processors.analytics_processor',
    'oioioi.status.processors.status_processor',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'oioioi.base.middleware.TimestampingMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'oioioi.base.middleware.AnnotateUserBackendMiddleware',
    'oioioi.su.middleware.SuAuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'linaro_django_pagination.middleware.PaginationMiddleware',
    'oioioi.contests.middleware.CurrentContestMiddleware',
    'oioioi.base.middleware.HttpResponseNotAllowedMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

COMMON_MEDIA_PREFIX = 'common/'

ROOT_URLCONF = 'oioioi.urls'

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

COMPRESS_ENABLED = True
COMPRESS_PARSER = 'compressor.parser.BeautifulSoupParser'
COMPRESS_PRECOMPILERS = (
    ('text/less', 'django-staticfiles-lessc {infile} {outfile}'),
)

INSTALLED_APPS = (
    # south needs to be before oioioi.base
    # because it overrides south's syncdb command
    'south',

    'oioioi.filetracker',
    'oioioi.contests',
    'oioioi.problems',
    'oioioi.programs',
    'oioioi.sinolpack',
    'oioioi.questions',
    'oioioi.rankings',
    'oioioi.sioworkers',
    'oioioi.jotform',
    'oioioi.analytics',
    'oioioi.celery',
    'oioioi.status',
    'oioioi.su',
    'oioioi.clock',
    'oioioi.base',

    'djcelery',
    'kombu.transport.django',
    'djsupervisor',
    'registration',
    'grappelli',
    'django_nose',
    'django_extensions',
    'debug_toolbar',
    'compressor',
    'linaro_django_pagination',

    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'oioioi.contests.auth.ContestPermissionsAuthBackend',
)

ACCOUNT_ACTIVATION_DAYS = 7

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = (
    '--verbosity=2',
    '--with-html',
    '--html-file=test_report.html',
    '-a!broken,!slow',
)

SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.CeleryBackend'
FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.media_root_factory'
DEFAULT_FILE_STORAGE = 'oioioi.filetracker.storage.FiletrackerStorage'

SUPERVISOR_AUTORELOAD_PATTERNS = [".py", ".pyc", ".pyo"]

# For linaro_django_pagination
PAGINATION_DEFAULT_WINDOW = 2
PAGINATION_DEFAULT_MARGIN = 1
FILES_ON_PAGE = 100
PROBLEMS_ON_PAGE = 100
QUESTIONS_ON_PAGE = 30
SUBMISSIONS_ON_PAGE = 100

NUM_DASHBOARD_SUBMISSIONS = 8
NUM_DASHBOARD_MESSAGES = 8

NUM_HINTS = 10
NUM_RECENT_CONTESTS = 5

REPLY_TEMPLATE_VISIBLE_NAME_LENGTH = 15

PROBLEM_SOURCES = (
    'oioioi.problems.problem_sources.PackageSource',
)

PROBLEM_PACKAGE_BACKENDS = (
    'oioioi.sinolpack.package.SinolPackageBackend',
)

SAFE_EXEC_MODE = 'vcpu'
SUBMITTABLE_EXTENSIONS = ['c', 'cc', 'cpp', 'pas']
USE_UNSAFE_EXEC = False
USE_LOCAL_COMPILERS = False
RUN_LOCAL_WORKERS = False

FILETRACKER_SERVER_ENABLED = False
FILETRACKER_LISTEN_ADDR = '127.0.0.1'
FILETRACKER_LISTEN_PORT = 9999

DEFAULT_CONTEST = None

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'oioioi': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

# Celery configuration

from sio.celery.default_config import *

BROKER_URL = 'django://'

CELERY_IMPORTS += [
    'oioioi.evalmgr',
]

CELERY_ROUTES.update({
    'oioioi.evalmgr.evalmgr_job': dict(queue='evalmgr'),
})

# Number of concurrently evaluated submissions
EVALMGR_CONCURRENCY = 1

# Split-priority evaluation
ENABLE_SPLITEVAL = False
SPLITEVAL_EVALMGR = False

# ID of JotForm account for "Send Feedback" link.
JOTFORM_ID = None

# Google Analytics
GOOGLE_ANALYTICS_TRACKING_ID = None

PRINTING_FONT_SIZE = 8  # in pt
PRINTING_MAX_FILE_SIZE = 1024 * 100  # in kB
PRINTING_MAX_FILE_PAGES = 10
PRINTING_COMMAND = ['lp']  # as argv list

# To get unlimited submissions count set to 0.
DEFAULT_SUBMISSIONS_LIMIT = 10
WARN_ABOUT_REPEATED_SUBMISSION = True

MAIL_ADMINS_ON_GRADING_ERROR = True
