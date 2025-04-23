import django

import sys

from oioioi.base.utils.finders import find_executable_path

if sys.version_info < (2, 6):
    raise RuntimeError("OIOIOI needs at least Python 2.6")

import os
import tempfile

from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

import oioioi

INSTALLATION_CONFIG_VERSION = 49

# Enable debugging features.
#
# SET DEBUG = False FOR PRODUCTION DEPLOYMENT.
DEBUG = False
INTERNAL_IPS = ('127.0.0.1',)

# Site name displayed in the title and used by sioworkersd
# to distinguish OIOIOI instances.
SITE_NAME = 'OIOIOI'
SITE_ID = 1

# The website address as it will be displayed to users in some places,
# including but not limited to the mail notifications.
PUBLIC_ROOT_URL = 'http://localhost'

# The server to be run. Options are:
# 'django' - django's http server
# 'uwsgi' - uwsgi daemon
# 'uwsgi-http' - uwsgi deamon with built-in http server
# 'none' - nothing will be ran
SERVER = os.getenv('OIOIOI_SERVER_MODE', 'none')

DATABASES = {
    'default': {
        'ENGINE': os.getenv('OIOIOI_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('OIOIOI_DB_NAME', 'oioioi'),              # Or path to database file if using sqlite3.
        'USER': os.getenv('OIOIOI_DB_USER', 'oioioi'),              # Not used with sqlite3.
        'PASSWORD': os.getenv('OIOIOI_DB_PASSWORD', 'password'),    # Not used with sqlite3.
        'HOST': os.getenv('OIOIOI_DB_HOST', 'db'),                  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': os.getenv('OIOIOI_DB_PORT', ''),                    # Set to empty string for default. Not used with sqlite3.
        'ATOMIC_REQUESTS': True,         # Don't touch unless you know what you're doing.
    }
}

# Controls if uwsgi in default configuration shall use gevent loop.
# To use it, you have to install gevent - please consult
# https://github.com/surfly/gevent
# This is recommended for heavy load, but you may still need to tune uwsgi
# options in deployment/supervisord.conf
UWSGI_USE_GEVENT = False

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

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
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = os.getenv('OIOIOI_TIMEZONE', 'UTC')

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'
LANGUAGE_COOKIE_NAME = 'lang'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LOCALE_PATHS = [
    os.path.join(os.path.dirname(oioioi.__file__), '_locale/locale'),
    os.path.join(os.path.dirname(oioioi.__file__), '_locale/locale-overrides'),
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
# Secret key can't be empty, it is overridden later.
SECRET_KEY = os.getenv('OIOIOI_SECRET', 'eca76a75-2b9f-4e09-8f88-86671acbed8b')

# Uncomment once oisubmit is used.
# OISUBMIT_MAGICKEY = '__OTHER_SECRET__'

# Email addresses to send error message reports.
ADMINS = (
    ('Your Name', 'youremail@example.com'),
)

# Email addresses to send communication from users (for example requests for
# teacher accounts).
MANAGERS = ADMINS

# SMTP server parameters for sending emails.
EMAIL_USE_TLS = False
EMAIL_HOST = 'mail'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_SUBJECT_PREFIX = '[OIOIOI] '

# Sender email address for messages sent by OIOIOI to users.
DEFAULT_FROM_EMAIL = 'webmaster@localhost'

# Sender email address for error messages sent to admins.
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Set to true to send user activation emails. Needs an SMTP server to be
# configured above.
SEND_USER_ACTIVATION_EMAIL = False

# List of callables that know how to import templates from various sources.
UNCACHED_TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

CACHED_TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', UNCACHED_TEMPLATE_LOADERS),
)

# Set to True to show the link to the problemset with contests on navbar.
PROBLEMSET_LINK_VISIBLE = True

# Set to true to show tags on the list of problems
PROBLEM_TAGS_VISIBLE = False

# Only relevant with PROBLEM_TAGS_VISIBLE set to True
SHOW_TAG_PROPOSALS_IN_PROBLEMSET = False

# Only relevant with SHOW_TAG_PROPOSALS_IN_PROBLEMSET set to True
PROBSET_SHOWN_TAG_PROPOSALS_LIMIT = 3
PROBSET_MIN_AMOUNT_TO_CONSIDER_TAG_PROPOSAL = 10

# Enables problem statistics at the cost of some per-submission performance hit.
# Set to True if you want to see statistics in the Problemset and problem sites.
# After enabling you should use ./manage.py recalculate_statistics
PROBLEM_STATISTICS_AVAILABLE = False

# Set to True to allow every logged in user to add problems directly to Problemset
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
                'oioioi.base.processors.navbar_links',
                'oioioi.base.processors.side_menus',
                'oioioi.base.processors.site_name',
                'oioioi.base.processors.mathjax_location',
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
    'oioioi.base.middleware.UserPreferencesMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'oioioi.maintenancemode.middleware.MaintenanceModeMiddleware',
)

COMMON_MEDIA_PREFIX = 'common/'

ROOT_URLCONF = 'oioioi.urls'

LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

COMPRESS_ENABLED = True
COMPRESS_PARSER = 'compressor.parser.BeautifulSoupParser'
COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)

LIBSASS_PRECISION = 8

# EXTRA MODULES
#
# Comment/uncomment components to disable/enable them.
#
# Additional components usually have to be prepended to the list in
# INSTALLED_APPS, because they may want to override some templates. But this is
# not always the case. Please consult the documentation of particular extension
# you're configuring.
#
# Some components need also corresponding lines in TEMPLATE_CONTEXT_PROCESSORS
# and/or AUTHENTICATION_BACKENDS commented/uncommented.

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
    'oioioi._locale',
    'oioioi.interactive',

    'djsupervisor',
    'registration',
    'django_extensions',
    'compressor',
    'dj_pagination',
    'mptt',

    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.forms',

    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'two_factor.plugins.phonenumber',

    'nested_admin',
    'coreapi',
    'rest_framework',
    'rest_framework.authtoken',

    'captcha',
    'fontawesomefree',
)

# If set to locations of flite and sox executables, enables audio playback
# of captcha. Audio output generated by flite (CAPTCHA_FLITE_PATH) is identical
# across multiple generations. To prevent potential security risk,
# CAPTCHA_SOX_PATH should be set as well, in order to inject random noise into
# audio files  generated by flite.
# If either sox or flite is installed and its location recognised by PATH
# variable, then corresponding setting will be set automatically.
CAPTCHA_FLITE_PATH = find_executable_path('flite')
CAPTCHA_SOX_PATH = find_executable_path('sox')
CAPTCHA_BACKGROUND_COLOR = '#daedf4'
CAPTCHA_IMAGE_SIZE = (250, 100)
CAPTCHA_FONT_SIZE = 64
CAPTCHA_LETTER_ROTATION = (-70, 70)

AUTHENTICATION_BACKENDS = (
    # 'oioioi.teachers.auth.TeacherAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
    'oioioi.contests.auth.ContestPermissionsAuthBackend',
)

ACCOUNT_ACTIVATION_DAYS = 7

FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.remote_storage_factory'
DEFAULT_FILE_STORAGE = 'oioioi.filetracker.storage.FiletrackerStorage'

FILETRACKER_SERVER_ENABLED = True
FILETRACKER_LISTEN_ADDR = os.getenv('FILETRACKER_LISTEN_ADDR', '127.0.0.1')
FILETRACKER_LISTEN_PORT = os.getenv('FILETRACKER_LISTEN_PORT', 9999)

# When using distributed workers set this to url on which workers will be
# able to access filetracker server. When 'remote_storage_factory' is used,
# this also defines the filetracker server oioioi should connect to.
FILETRACKER_URL = os.getenv('FILETRACKER_URL', 'http://127.0.0.1:9999')

# When using a remote storage it's recommended to enable a cache cleaner deamon
# which will periodically scan cache directory and remove files what aren't
# used. For a detailed description of each option, please read a cache cleaner
# configuration section in the sioworkersd documentation. Please note that
# the cache cleaner can delete *any* file found under FILETRACKER_CACHE_ROOT
# directory, so don't store other files there (unless you want them to be
# periodically deleted).
# FILETRACKER_CACHE_CLEANER_ENABLED = True
# FILETRACKER_CACHE_CLEANER_SCAN_INTERVAL = '1h'
# FILETRACKER_CACHE_CLEANER_CLEAN_LEVEL = '50'
# FILETRACKER_CACHE_SIZE = '8G'

SUPERVISOR_AUTORELOAD_PATTERNS = [".py", ".pyc", ".pyo"]

# For dj_pagination
PAGINATION_DEFAULT_WINDOW = 4
PAGINATION_DEFAULT_MARGIN = 1
FILES_ON_PAGE = 100
PROBLEMS_ON_PAGE = 100
CONTESTS_ON_PAGE = 20
QUESTIONS_ON_PAGE = 30
SUBMISSIONS_ON_PAGE = 100
PARTICIPANTS_ON_PAGE = 100
TESTS_ON_PAGE = 100

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

SIOWORKERSD_URL = 'http://localhost:7889/'
SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.SioworkersdBackend'

# Set this to false if you don't need sioworkersd instance (e. g.
# because you use instance started by another instance of OIOIOI)
RUN_SIOWORKERSD = True

# On which interface should the sioworkers receiver listen. You should
# set the address to 0.0.0.0 if you want remote workers to access
# your server.
SIOWORKERS_LISTEN_ADDR = '127.0.0.1'
SIOWORKERS_LISTEN_PORT = 7890

# URL to which sioworkersd should respond, when it has finished its job
# When set to None the default url will be created using the pattern
# http://$SIOWORKERS_LISTEN_ADDR:$SIOWORKERS_LISTEN_PORT
SIOWORKERS_LISTEN_URL = None

# Set to false to disable workers running on the server machine.
RUN_LOCAL_WORKERS = False

# This setting specifies which languages are available on the platform.
# Each language must contain type and display_name entry. Such an entry may be useful
# if it is to contain characters, that probably shouldn't be allowed in the
# language identifier, such as '#'. Languages of type 'main'
# ('main' is default type, it doesn't need to be set)
# are enabled on every problem by default, languages of type 'extra'
# can only be enabled on a problem by adding them to the problems white list.
SUBMITTABLE_LANGUAGES = {
    'C': {
        'display_name': 'C'
    },
    'C++': {
        'display_name': 'C++'
    },
    'Pascal': {
        'display_name': 'Pascal'
    },
    'Java': {
        'display_name': 'Java'
    },
    'Python': {
        'display_name': 'Python'
    },
    'Output-only': {
        'type': 'extra',
        'display_name': 'Output-only',
    }
}

# This setting is used for associating programming languages with file extensions.
# There should be an entry for every language supported with key being the same
# as in SUBMITTABLE_LANGUAGES.
SUBMITTABLE_EXTENSIONS = {'C': ['c'], 'C++': ['cpp', 'cc'], 'Pascal': ['pas'],
                          'Java': ['java'], 'Python': ['py'], 'Output-only': ['txt', 'out']}

# This setting specifies which compilers are available in sioworkers.
# By default that means ones defined here:
# https://github.com/sio2project/sioworkers/blob/master/setup.py#L71
# There should be an entry for every language supported with key being the same
# as in SUBMITTABLE_LANGUAGES. Additionally each compiler must contain a
# display_name entry.
AVAILABLE_COMPILERS = {
    'C': {
        'gcc4_8_2_c99': {'display_name': 'gcc:4.8.2 std=gnu99'}
    },
    'C++': {
        'g++4_8_2_cpp11': {'display_name': 'g++:4.8.2 std=c++11'}
    },
    'Pascal': {
        'fpc2_6_2': {'display_name': 'fpc:2.6.2'}
    },
    'Java': {
        'java1_8': {'display_name': 'java:1.8'}
    },
    'Python': {
        'python': {'display_name': 'python'}
    },
    'Output-only': {
        'output-only': {'display_name': 'output-only'}
    }
}

SYSTEM_COMPILERS = {
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
    },
    'Output-only': {
        'output-only': {'display_name': 'output-only'}
    }
}

# This setting sets the default compilers used throughout the platform.
# There should be an entry for every language supported with key being the same
# as in SUBMITTABLE_LANGUAGES and value contained in AVAILABLE_COMPILERS.
DEFAULT_COMPILERS = {'C': 'gcc4_8_2_c99', 'C++': 'g++4_8_2_cpp11',
                     'Pascal': 'fpc2_6_2', 'Java': 'java1_8',
                     'Python': 'python', 'Output-only': 'output-only'}

SYSTEM_DEFAULT_COMPILERS = {'C': 'system-gcc', 'C++': 'system-g++',
                            'Pascal': 'system-fpc', 'Java': 'system-java',
                            'Python': 'system-python', 'Output-only': 'output-only'}

# This is a legacy option for szkopul backwards compatibility.
# Shouldn't be changed unless you know what you are doing.
# Languages added here will use DEFAULT_COMPILERS for non-makefile sinol packages.
OVERRIDE_COMPILER_LANGS = []

# Set the following option to false to enable the safe execution supervisor.
USE_UNSAFE_EXEC = False

# Default safe execution tool
# You can change the safe execution tool. Current options are:
# - "sio2jail" - (default) SIO2Jail
# - "cpu" - ptrace (measures real time)
DEFAULT_SAFE_EXECUTION_MODE = "sio2jail"

# WARNING: setting this to False is experimental until we make sure that
# checkers do work well in sandbox
#
# Setting this to False will run checkers in sandbox. This option is
# independent to USE_UNSAFE_EXEC.
USE_UNSAFE_CHECKER = True

# When USE_SINOLPACK_MAKEFILES equals True, the sinolpack upload workflow uses
# standard sinolpack makefiles, whose behaviour may be modified by a custom
# makefile.user file from a package. The makefiles' execution is not sandboxed,
# hence it should be disabled for untrusted contest admins.
# When it equals False, the upload workflow uses sioworkers for programs'
# execution (in a sandboxed environment, if USE_UNSAFE_EXEC is set to False).
USE_SINOLPACK_MAKEFILES = True

# When set to True untrusted users cannot upload sinol packages containing
# problem statement in HTML format (they must use PDF).
# Trusted users are users with superuser access or teachers (if oioioi.teachers
# app is enabled). This option has no effect for packages uploaded
# by management commands or if USE_SINOLPACK_MAKEFILES is enabled.
# We suggest enabling it when using oioioi.usercontests app.
SINOLPACK_RESTRICT_HTML = False

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

# Memory limit for input generator job.
# This is a legacy option for szkopul backwards compatibility.
# Shouldn't be changed unless you know what you are doing.
# INGEN_MEMORY_LIMIT = 512 * 1024

DEFAULT_CONTEST = None
ONLY_DEFAULT_CONTEST = False

# Contest mode - automatic activation of contests.
#
# Available choices are:
#   ContestMode.neutral - no contest is activated automatically,
# users have to explicitly enter into a contest specific page if they want
# to participate. They can visit both contest specific as well as non-contest
# specific pages.
#   ContestMode.contest_if_possible - if there exists a contest, users
# are automatically redirected to one when visiting a page which
# has a contest specific version, e.g. visiting index ('/') could redirect
# to "c" contest's dashboard page ('/c/c/dashboard') if there existed
# a contest "c". The contest picking algorithm is described in detail
# in oioioi.contests.middleware module.
# If a page requires that no contest is active (e.g. user's portal page
# from the "portals" app), it can still be visited and no redirection
# will be made.
#   ContestMode.contest_only - this setting is similar to the previous one
# except that pages requiring no contest to be active can only be visited
# by superusers (other users get "403 - Permission Denied").
#
# Some features may depend on this setting, e.g. the "portals" app requires
# that either the "neutral" or the "contest_if_possible" option is picked.
from oioioi.contests.current_contest import ContestMode
CONTEST_MODE = ContestMode.contest_if_possible

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
        },
        'celery': {
            'handlers': ['console', 'emit_notification'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

# Limits the duration of user contests.
# Comment out if you don't want to limit the user contests duration.
# import pytz
# from datetime import datetime
# USER_CONTEST_TIMEOUT = datetime(2020, 2, 7, 23, 0, 0, tzinfo=pytz.utc)

# Celery configuration

CELERY_QUEUES = {}
CELERY_RESULT_BACKEND = 'rpc'
CELERY_ACKS_LATE = True
CELERY_SEND_EVENTS = True

BROKER_URL = 'sqla+sqlite:///' + os.path.join(tempfile.gettempdir(),
                                              'celerydb.sqlite')

# RabbitMQ connection settings
host = os.getenv("RABBITMQ_HOST", None)
port = os.getenv("RABBITMQ_PORT", None)
user = os.getenv("RABBITMQ_USER", None)
password = os.getenv("RABBITMQ_PASSWORD", None)

if (
    host is not None
    and port is not None
    and user is not None
    and password is not None
):
    BROKER_URL = f"amqp://{user}:{password}@{host}:{port}"

CELERY_IMPORTS = [
    'oioioi.evalmgr.tasks',
    'oioioi.problems.unpackmgr',
]

CELERY_ROUTES = {
    'oioioi.evalmgr.tasks.evalmgr_job': dict(queue='evalmgr'),
    'oioioi.problems.unpackmgr.unpackmgr_job': dict(queue='unpackmgr'),
}

# Number of concurrently evaluated submissions
EVALMGR_CONCURRENCY = 1

# Number of concurrently processed problem packages
UNPACKMGR_CONCURRENCY = 1

# Email address for "Send Feedback" message.
SZKOPUL_SUPPORT_EMAIL = None

# Google Analytics
GOOGLE_ANALYTICS_TRACKING_ID = None

# Consent texts
REGISTRATION_RULES_CONSENT = _("terms accepted")
REGISTRATION_MARKETING_CONSENT = None
REGISTRATION_PARTNER_CONSENT = None

PRINTING_FONT_SIZE = 8  # in pt
PRINTING_MAX_FILE_SIZE = 1024 * 100  # in kB
PRINTING_MAX_FILE_PAGES = 10
PRINTING_COMMAND = ['lp', '-o landscape', '-o sides=two-sided-short-edge']

# To get unlimited submissions count set to 0.
DEFAULT_SUBMISSIONS_LIMIT = 10
WARN_ABOUT_REPEATED_SUBMISSION = True
DEFAULT_SUBMISSION_SIZE_LIMIT = 1024 * 100  # in bytes

# Only used if 'testrun' app is enabled.
# To get unlimited test runs set to 0.
DEFAULT_TEST_RUNS_LIMIT = 10

MAIL_ADMINS_ON_GRADING_ERROR = True

# Message shortcut length in notification shown when an admin is editing
# a reply in a thread in which a new message was posted in the meantime.
MEANTIME_ALERT_MESSAGE_SHORTCUT_LENGTH = 50

SHARING_SERVERS = (
   # ('site_url', 'sharing_url', 'client_id', 'client_secret'),
)

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

# Complaints
# COMPLAINTS_EMAIL = 'email_to_send_complaints_to'
# COMPLAINTS_SUBJECT_PREFIX = '[oioioi-complaints] '

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
    ),
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}

# If set to True, usercontests will become read-only: it will be impossible to
# change, delete or submit to existing usercontests, as well as add new ones.
# This operation is fully reversible.
ARCHIVE_USERCONTESTS = False

# This is a legacy option for szkopul backwards compatibility.
# Shouldn't be changed unless you know what you are doing.
# If set to True, usercontests will behave like teachercontests
# and will not be listed on the main page.
# Changing this setting is reversible.
HIDE_USERCONTESTS = False

FORUM_PAGE_SIZE = 15
FORUM_THREADS_PER_PAGE = 30
FORUM_POSTS_PER_PAGE = 30
FORUM_POST_MAX_LENGTH = 20000
FORUM_REACTIONS_TO_DISPLAY = 10

# Check seems to be broken. https://stackoverflow.com/a/65578574
SILENCED_SYSTEM_CHECKS = ['admin.E130']

# Experimental
USE_ACE_EDITOR = False

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/day',
    'user': '1000/hour'
}
