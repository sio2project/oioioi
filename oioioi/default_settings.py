# pylint: disable=wildcard-import
import sys
if sys.version_info < (2, 6):
    raise RuntimeError("OIOIOI needs at least Python 2.6")

import os
import tempfile

os.environ.setdefault('CELERY_LOADER', 'oioioi.celery.loaders.OioioiLoader')
import djcelery
djcelery.setup_loader()

import oioioi
from oioioi.contests.current_contest import ContestMode

from django.contrib.messages import constants as messages

INSTALLATION_CONFIG_VERSION = 32

DEBUG = False
INTERNAL_IPS = ('127.0.0.1',)

# Site name displayed in the title and used by sioworkersd
# to distinguish OIOIOI instances.
SITE_NAME = 'OIOIOI'

# The website address as it will be displayed to users in some places,
# including but not limited to the mail notifications.
PUBLIC_ROOT_URL = 'http://localhost'

# Run uwsgi daemon. Shall be True, False or 'auto'.
# 'auto' means daemon will be run iff DEBUG is disabled.
UWSGI_ENABLED = 'auto'

UWSGI_USE_GEVENT = False

LANGUAGES = (
    ('en', 'English'),
    ('pl', 'Polish'),
)

STATEMENT_LANGUAGES = (
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
UNCACHED_TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

CACHED_TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', UNCACHED_TEMPLATE_LOADERS),
)

PROBLEMSET_LINK_VISIBLE = True

PROBLEM_TAGS_VISIBLE = False

PROBLEM_STATISTICS_AVAILABLE = False

EVERYBODY_CAN_ADD_TO_PROBLEMSET = False

DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'oioioi.su.processors.real_user',
                'oioioi.base.processors.base_url',
                'oioioi.base.processors.side_menus',
                'oioioi.base.processors.site_name',
                'oioioi.base.processors.mathjax_location',
                'oioioi.jotform.processors.jotform',
                'oioioi.contests.processors.register_current_contest',
                'oioioi.contests.processors.register_recent_contests',
                'oioioi.contestexcl.processors.register_contest_exclusive',
                'oioioi.problems.processors.dangling_problems_processor',
                'oioioi.problems.processors.problemset_link_visible_processor',
                'oioioi.problems.processors.problems_need_rejudge_processor',
                'oioioi.problems.processors.can_add_to_problemset_processor',
                'oioioi.questions.processors.navbar_tip_processor',
                'oioioi.analytics.processors.analytics_processor',
                'oioioi.status.processors.status_processor',
                'oioioi.programs.processors.drag_and_drop_processor',
            ],
        },
    },
]

MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'oioioi.base.middleware.TimestampingMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',  # must be after AuthenticationMiddleware
    'oioioi.base.middleware.AnnotateUserBackendMiddleware',
    'oioioi.su.middleware.SuAuthenticationMiddleware',
    'oioioi.su.middleware.SuFirstTimeRedirectionMiddleware',
    'oioioi.base.middleware.UserInfoInErrorMessage',
    'django.contrib.messages.middleware.MessageMiddleware',
    'dj_pagination.middleware.PaginationMiddleware',
    'oioioi.contests.middleware.CurrentContestMiddleware',
    'oioioi.base.middleware.HttpResponseNotAllowedMiddleware',
    'oioioi.base.middleware.CheckLoginMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'oioioi.maintenancemode.middleware.MaintenanceModeMiddleware',
)

COMMON_MEDIA_PREFIX = 'common/'

ROOT_URLCONF = 'oioioi.urls'

LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

COMPRESS_ENABLED = True
COMPRESS_PARSER = 'compressor.parser.BeautifulSoupParser'
COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)

LIBSASS_PRECISION = 8

INSTALLED_APPS = (
    'debug_toolbar',
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
    'oioioi.dashboard',
    'oioioi.base',
    'oioioi.maintenancemode',
    'oioioi.evalmgr',
    'oioioi.workers',
    'oioioi.quizzes',

    'djcelery',
    'kombu.transport.django',
    'djsupervisor',
    'registration',
    'django_extensions',
    'compressor',
    'dj_pagination',
    'mptt',
    'overextends',
    'raven.contrib.django.raven_compat',

    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',

    'nested_admin',
    'coreapi',
    'rest_framework',
    'rest_framework.authtoken',
)

AUTHENTICATION_BACKENDS = (
    # 'oioioi.teachers.auth.TeacherAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
    'oioioi.contests.auth.ContestPermissionsAuthBackend',
)

ACCOUNT_ACTIVATION_DAYS = 7

SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.SioworkersdBackend'
FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.remote_storage_factory'
DEFAULT_FILE_STORAGE = 'oioioi.filetracker.storage.FiletrackerStorage'

SUPERVISOR_AUTORELOAD_PATTERNS = [".py", ".pyc", ".pyo"]

# For dj_pagination
PAGINATION_DEFAULT_WINDOW = 4
PAGINATION_DEFAULT_MARGIN = 1
FILES_ON_PAGE = 100
PROBLEMS_ON_PAGE = 100
QUESTIONS_ON_PAGE = 30
SUBMISSIONS_ON_PAGE = 100
PARTICIPANTS_ON_PAGE = 100
TESTS_ON_PAGE = 100
PRIZES_ON_PAGE = 100

NUM_PANEL_SUBMISSIONS = 7

NUM_DASHBOARD_SUBMISSIONS = 8
NUM_DASHBOARD_MESSAGES = 8

NUM_HINTS = 10
NUM_RECENT_CONTESTS = 7
NUM_RECENT_IN_MENU = 5

REPLY_TEMPLATE_VISIBLE_NAME_LENGTH = 15

PROBLEM_SOURCES = (
    'oioioi.problems.problem_sources.UploadedPackageSource',
    'oioioi.problems.problem_sources.ProblemsetSource',
    'oioioi.quizzes.problem_sources.EmptyQuizSource',
)

PROBLEM_PACKAGE_BACKENDS = (
    'oioioi.sinolpack.package.SinolPackageBackend',
)

# This setting is used for associating allowed programming languages with file
# extensions. Allowed languages are determined by contest and problem
# controllers.
SUBMITTABLE_EXTENSIONS = {'C': ['c'], 'C++': ['cpp', 'cc'], 'Pascal': ['pas'],
                          'Java': ['java'], 'Python': ['py']}
USE_UNSAFE_EXEC = False
USE_LOCAL_COMPILERS = False
DEFAULT_SAFE_EXECUTION_MODE = "vcpu"
RUN_LOCAL_WORKERS = False

# WARNING: experimental, see settings template
USE_UNSAFE_CHECKER = True

# When USE_SINOLPACK_MAKEFILES equals True, the sinolpack upload workflow uses
# standard sinolpack makefiles, whose behaviour may be modified by a custom
# makefile.user file from a package. The makefiles' execution is not sandboxed,
# hence it should be disabled for untrusted contest admins.
# When it equals False, the upload workflow uses sioworkers for programs'
# execution (in a sandboxed environment, if USE_UNSAFE_EXEC is set to False).
USE_SINOLPACK_MAKEFILES = True

# Scorers below are used for judging submissions without contests,
# eg. submitting to problems from problemset.
DEFAULT_TEST_SCORER = \
    'oioioi.programs.utils.discrete_test_scorer'
DEFAULT_GROUP_SCORER = \
    'oioioi.programs.utils.min_group_scorer'
DEFAULT_SCORE_AGGREGATOR = \
    'oioioi.programs.utils.sum_score_aggregator'

# Upper bounds for tests' time [ms] and memory [KiB] limits.
MAX_TEST_TIME_LIMIT_PER_PROBLEM = 1000 * 60 * 60 * 30
MAX_MEMORY_LIMIT_FOR_TEST = 256 * 1024

FILETRACKER_SERVER_ENABLED = True
FILETRACKER_LISTEN_ADDR = '127.0.0.1'
FILETRACKER_LISTEN_PORT = 9999

FILETRACKER_URL = 'http://127.0.0.1:9999'

RUN_SIOWORKERSD = True

DEFAULT_CONTEST = None
ONLY_DEFAULT_CONTEST = False

CONTEST_MODE = ContestMode.contest_if_possible

SEND_USER_ACTIVATION_EMAIL = True

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
    'formatters': {
            'date_and_level': {
                'format': '[%(asctime)s %(levelname)s %(process)d:%(thread)d]'
                          ' %(message)s',
            },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'date_and_level',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'emit_notification': {
            'level': 'DEBUG',
            'class': 'oioioi.base.notification.NotificationHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'oioioi': {
            'handlers': ['console', 'emit_notification'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

# Celery configuration

from sio.celery.default_config import *

BROKER_URL = 'sqla+sqlite:///' + os.path.join(tempfile.gettempdir(),
                                             'celerydb.sqlite')

# pylint: disable=undefined-variable

CELERY_IMPORTS += [
    'oioioi.evalmgr.tasks',
    'oioioi.problems.unpackmgr',
]

CELERY_ROUTES.update({
    'oioioi.evalmgr.tasks.evalmgr_job': dict(queue='evalmgr'),
    'oioioi.problems.unpackmgr.unpackmgr_job': dict(queue='unpackmgr'),
})

# Number of concurrently evaluated submissions
EVALMGR_CONCURRENCY = 1

# Number of concurrently processed problem packages
UNPACKMGR_CONCURRENCY = 1

SIOWORKERSD_URL = 'http://localhost:7889/'

# ID of JotForm account for "Send Feedback" link.
JOTFORM_ID = None

# Google Analytics
GOOGLE_ANALYTICS_TRACKING_ID = None

PRINTING_FONT_SIZE = 8  # in pt
PRINTING_MAX_FILE_SIZE = 1024 * 100  # in kB
PRINTING_MAX_FILE_PAGES = 10
PRINTING_COMMAND = ['lp', '-o landscape', '-o sides=two-sided-short-edge']

# To get unlimited submissions count set to 0.
DEFAULT_SUBMISSIONS_LIMIT = 10
WARN_ABOUT_REPEATED_SUBMISSION = True

# Only used if 'testrun' app is enabled.
# To get unlimited test runs set to 0.
DEFAULT_TEST_RUNS_LIMIT = 10

MAIL_ADMINS_ON_GRADING_ERROR = True

# Message shortcut length in notification shown when an admin is editing
# a reply in a thread in which a new message was posted in the meantime.
MEANTIME_ALERT_MESSAGE_SHORTCUT_LENGTH = 50

# Zeus configuration
ZEUS_INSTANCES = {
}

# URL prefix (protocol, hostname and port)
# hit by the Zeus callback after a submission is judged
ZEUS_PUSH_GRADE_CALLBACK_URL = 'https://sio2.dasie.mimuw.edu.pl'

# Delay between consecutive http requests for results.
ZEUS_RESULTS_FETCH_DELAY = 3  # seconds
ZEUS_CONNECTION_TIMEOUT = 10  # seconds
ZEUS_SEND_RETRIES = 3
ZEUS_RETRY_SLEEP = 1  # second

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(tempfile.gettempdir(), 'oioioi-cache')
    }
}

# Ranking
RANKINGSD_POLLING_INTERVAL = 0.5  # seconds
RANKING_COOLDOWN_FACTOR = 2  # seconds
RANKING_MIN_COOLDOWN = 5  # seconds
RANKING_MAX_COOLDOWN = 100  # seconds

# Notifications configuration (client)
# This one is for JavaScript socket.io client.
# It should contain actual URL available from remote machines.
NOTIFICATIONS_SERVER_URL = 'http://localhost:7887/'

# Notifications configuration (server)
NOTIFICATIONS_SERVER_ENABLED = False

# URL connection string to a Notifications Server instance
NOTIFICATIONS_OIOIOI_URL = 'http://localhost:8000/'

# URL connection string for RabbitMQ instance used by Notifications Server
NOTIFICATIONS_RABBITMQ_URL = 'amqp://localhost'

# Extra arguments for pika ConnectionParameters, see
# https://pika.readthedocs.io/en/stable/modules/parameters.html
NOTIFICATIONS_RABBITMQ_EXTRA_PARAMS = {}

# Port that the Notifications Server listens on
NOTIFICATIONS_SERVER_PORT = 7887

# Balloons
BALLOON_ACCESS_COOKIE_EXPIRES_DAYS = 7

# Cache timeout (in seconds) for livedata stream (used in some onsite
# competitions to show results online). Does not influence the data for
# admins or observers.
LIVEDATA_CACHE_TIMEOUT = 30

# Submissions by (snail) mail
MAILSUBMIT_CONFIRMATION_HASH_LENGTH = 5

# On which interface should the sioworkers receiver listen
SIOWORKERS_LISTEN_ADDR = '127.0.0.1'
SIOWORKERS_LISTEN_PORT = 7890

# URL to which should respond sioworkersd, when it has finished its job
# When set to None the default url will be created using the pattern
# http://$SIOWORKERS_LISTEN_ADDR:$SIOWORKERS_LISTEN_PORT
SIOWORKERS_LISTEN_URL = None

# Maintenance mode settings
CONTEST_PREFIX_RE = '^(/c/[a-z0-9_-]+)?'
MAINTENANCE_MODE_REDIRECT_URL = '/maintenance/'
MAINTENANCE_MODE_IGNORE_URLS = [
    CONTEST_PREFIX_RE + MAINTENANCE_MODE_REDIRECT_URL + '$',
    CONTEST_PREFIX_RE + '/login/$',
    CONTEST_PREFIX_RE + '/logout/$',
]

# Domain to use for serving IP to hostname mappings
# using ./manage.py ipauth-dnsserver
IPAUTH_DNSSERVER_DOMAIN = None

# Judging priority and weight settings
DEFAULT_CONTEST_PRIORITY = 10
DEFAULT_CONTEST_WEIGHT = 1000
OIOIOI_INSTANCE_PRIORITY_BONUS = 0
OIOIOI_INSTANCE_WEIGHT_BONUS = 0
NON_CONTEST_PRIORITY = 0
NON_CONTEST_WEIGHT = 1000

# Interval [in seconds] for mailnotifyd to wait before scanning the database
# for new messages to notify about
MAILNOTIFYD_INTERVAL = 60

# If your contest has no access to the internet and you need MathJax typesetting,
# either whitelist this link or download your own copy of MathJax and link it here.
MATHJAX_LOCATION = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/"

# Django message framework CSS classes
# https://docs.djangoproject.com/en/1.9/ref/contrib/messages/#message-tags
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

USE_API = True

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    )
}
