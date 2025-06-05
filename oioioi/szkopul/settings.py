# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from django.utils.safestring import mark_safe
from oioioi.default_settings import *
from oioioi.contests.current_contest import ContestMode

# This should match INSTALLATION_CONFIG_VERSION in
# "oioioi/default_settings.py".
# Before you adjust it, you may consider visiting
# "https://github.com/sio2project/oioioi/#changes-in-the-deployment-directory".
CONFIG_VERSION = 49

SITE_ID = 1

SERVER = 'uwsgi'

# Enable debugging features.
#
# COMMENT THIS OUT FOR PRODUCTION DEPLOYMENT.
DEBUG = True

# Bonus to judging priority ang judging weight for each contest on this
# OIOIOI instance.
OIOIOI_INSTANCE_PRIORITY_BONUS = 20
# OIOIOI_INSTANCE_WEIGHT_BONUS = 0

# (13.12.2017 - we removed these lines)
# if DEBUG:
#    TEMPLATE_LOADERS = UNCACHED_TEMPLATE_LOADERS
if DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = UNCACHED_TEMPLATE_LOADERS
else:
    # Cache compiled templates in production environment.
    TEMPLATES[0]['OPTIONS']['loaders'] = CACHED_TEMPLATE_LOADERS

# The APP_DIRS option is allowed only in template engines that have no custom
# loaders specified.
TEMPLATES[0]['APP_DIRS'] = False


# Site name displayed in the title and used by sioworkersd
# to distinguish OIOIOI instances.
SITE_NAME = 'SZKOpuł'

# The website address as it will be displayed to users in some places,
# including but not limited to the mail notifications.
# Defaults to 'http://localhost'.
PUBLIC_ROOT_URL = 'https://szkopul.edu.pl/'

# Sender email address for messages sent by OIOIOI to users.
DEFAULT_FROM_EMAIL = 'sio2@sio2project.mimuw.edu.pl'
DEFAULT_FROM_ADDRESS = DEFAULT_FROM_EMAIL

# Sender email address for error messages sent to admins.
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email addresses to send communication from users (for example requests for
# teacher accounts).
MANAGERS = (
    ('Szkopul Admin', 'sio2@sio2project.mimuw.edu.pl'),
)

# Registration checkbox descriptions


REGISTRATION_RULES_CONSENT = mark_safe(
    "Wyrażam "
    "<a target=\"_blank\" href=\"/rodo/zgoda/\">"
    " zgodę na przetwarzanie moich ww. danych osobowych</a>"
    " oraz oświadczam,"
    " że zapoznałam/zapoznałem się z "
    "<a target=\"_blank\" href=\"/rodo/\">klauzulą informacyjną</a>")

# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['szkopul.edu.pl', 'szk.oioioi.edu.pl',
                 'snag.dasie.mimuw.edu.pl', 'snag', 'szkopul', 'szkopul2', 'localhost']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Warsaw'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGES = (
    ('pl', 'polski'),
    ('en', 'english'),
)
LANGUAGE_CODE = 'pl'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/sio2/deployment/media'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/sio2/deployment/static'

# Compress templates offline
COMPRESS_OFFLINE = True

# SMTP server parameters for sending emails.
EMAIL_SUBJECT_PREFIX = '[Szkopul] '
EMAIL_USE_TLS = False
EMAIL_HOST = 'mail'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

# Comment to send user activation emails. Needs an SMTP server to be
# configured above.
SEND_USER_ACTIVATION_EMAIL = False

# RabbitMQ server URL for distributed workers.
#
# Uncomment once RabbitMQ is installed. By default SQLAlchemy database is used,
# but this is unreliable and not intended for production.
BROKER_URL = 'amqp://guest:guest@localhost:5672//'

# Filetracker server settings.
#
# Uncomment the following lines to enable remote access to Filetracker. This is
# needed if you install separate judging machines. Beware -- there is no
# authorization mechanism in Filetracker. Everyone who can access the server on
# the given port will be able to see all the files. It's recommended to have
# the judging machines on a separate physical network and listen only on the
# corresponding IP address.

# FT-MIG
# FILETRACKER_SERVER_ENABLED = True
FILETRACKER_SERVER_ENABLED = False
FILETRACKER_LISTEN_ADDR = '0.0.0.0'
FILETRACKER_LISTEN_PORT = 9999

# When using distributed workers set this to url on which workers will be
# able to access filetracker server.
# FT-MIG
# FILETRACKER_URL = 'http://szkopul:9999'
FILETRACKER_URL = 'http://filetracker-szkopul:19999'

# FT-MIG
#
FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.remote_storage_factory'

# When using a remote_storage_factory it's necessary to specify a cache
# directory in which necessary files will be stored.
FILETRACKER_CACHE_ROOT = '/sio2/deployment/cache'

# When using a remote storage it's recommended to enable a cache cleaner deamon
# which will periodically scan cache directory and remove files what aren't
# used. For a detailed description of each option, please read a cache cleaner
# configuration section in the sioworkersd documentation.
FILETRACKER_CACHE_CLEANER_ENABLED = False
FILETRACKER_CACHE_CLEANER_SCAN_INTERVAL = '1h'
FILETRACKER_CACHE_CLEANER_CLEAN_LEVEL = '85'
FILETRACKER_CACHE_SIZE = '16G'

# On which interface should the sioworkers receiver listen. You should
# set the address to 0.0.0.0 if you want remote workers to access
# your server.
SIOWORKERS_LISTEN_ADDR = '0.0.0.0'
SIOWORKERS_LISTEN_PORT = 7890

# URL to which should respond sioworkersd, when it has finished its job
# When set to None the default url will be created using the pattern
# http://$SIOWORKERS_LISTEN_ADDR:$SIOWORKERS_LISTEN_PORT
SIOWORKERS_LISTEN_URL = 'http://snag:7890/'

# Set this to false if you don't need sioworkersd instance (e. g.
# because you use instance started by another instance of OIOIOI)
RUN_SIOWORKERSD = False

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
    # 'Java': {
    #    'display_name': 'Java'
    # },
    'Python': {
        'display_name': 'Python'
    },
}

SUBMITTABLE_EXTENSIONS = {
    'C': ['c'],
    'C++': ['cpp', 'cc'],
    'Pascal': ['pas'],
    # 'Java': ['java'],
    'Python': ['py'],
}

# This setting specifies which compilers are available in sioworkers.
# By default that means ones defined here:
# https://github.com/sio2project/sioworkers/blob/master/setup.py#L71
AVAILABLE_COMPILERS = {
    'C': {
        'gcc4_8_2_c99': {'display_name': 'gcc:4.8.2 std=gnu99'}
    },
    'C++': {
        'g++4_8_2_cpp11': {'display_name': 'g++:4.8.2 std=c++11'},
        'g++8_3_cpp17': {'display_name': 'g++:8.3 std=c++17'},
        'g++8_3_cpp17_amd64': {'display_name': 'g++:8.3 std=c++17 x64'},
        'g++10_2_cpp17_amd64': {'display_name': 'g++:10.2 std=c++17 x64'}
    },
    'Pascal': {
        'fpc2_6_2': {'display_name': 'fpc:2.6.2'}
    },
    # 'Java': {
    #    'java1_8': {'display_name': 'java:1.8'}
    # },
    'Python': {
        'python_3_4_numpy': {'display_name': 'python:3.4 + numpy'},
        'python_3_7_numpy': {'display_name': 'python:3.7 + numpy'},
        'python_3_9_numpy': {'display_name': 'python:3.9 + numpy'}
    },
}

# This setting sets the default compilers used throughout the platform.
# By uncommenting the below dict you can change all or any one of them.
DEFAULT_COMPILERS = {
    'C': 'gcc4_8_2_c99',
    'C++': 'g++8_3_cpp17',
    'Pascal': 'fpc2_6_2',
    # 'Java': 'java1_8',
    'Python': 'python_3_7_numpy',
}

# FIXME: add this to repo
SIOWORKERSD_URL = 'http://sioworkersd:7889/'

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
#
# The default setting is "contest_if_possible".
CONTEST_MODE = ContestMode.neutral


# When USE_SINOLPACK_MAKEFILES equals True, the sinolpack upload workflow uses
# standard sinolpack makefiles, whose behaviour may be modified by a custom
# makefile.user file from a package. The makefiles' execution is not sandboxed,
# hence it should be disabled for untrusted contest admins.
# Whet it equals False, the upload workflow uses sioworkers for programs'
# execution (in a sandboxed environment, if USE_UNSAFE_EXEC is set to False).
USE_SINOLPACK_MAKEFILES = False

# When set to True untrusted users cannot upload sinol packages containing
# problem statement in HTML format (they must use PDF).
# Trusted users are users with superuser access or teachers (if oioioi.teachers
# app is enabled). This option has no effect for packages uploaded
# by management commands or if USE_SINOLPACK_MAKEFILES is enabled.
# We suggest enabling it when using oioioi.usercontests app.
SINOLPACK_RESTRICT_HTML = False

# Upper bounds for tests' time [ms] and memory [KiB] limits.
MAX_TEST_TIME_LIMIT_PER_PROBLEM = 1000 * 60 * 60 * 30
# MAX_MEMORY_LIMIT_FOR_TEST = 520 * 1024
MAX_MEMORY_LIMIT_FOR_TEST = 1024 * 1024

# Controls if uwsgi in default configuration shall use gevent loop.
# To use it, you have to install gevent - please consult
# https://github.com/surfly/gevent
# This is recommended for heavy load, but you may still need to tune uwsgi
# options in deployment/supervisord.conf
UWSGI_USE_GEVENT = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

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
    #    'szkopul',
    'oioioi.teams',
    #    'oioioi.contestlogo',
    'oioioi.teachers',
    #    'oioioi.ipdnsauth',
    #    'oioioi.sio1sync',
    'oioioi.participants',
    #    'oioioi.oi',
    'oioioi.contestexcl',
    #    'oioioi.oisubmit',
    #    'oioioi.zeus',
    #    'oioioi.testrun',
    #    'oioioi.spliteval',
    #    'oioioi.printing',
    'oioioi.scoresreveal',
    #    'oioioi.oireports',
    #    'oioioi.ontak',
    #    'oioioi.complaints',
    #    'oioioi.confirmations',
    #    'oioioi.acm',
    #    'oioioi.forum',
    #    'oioioi.disqualification',
    #    'oioioi.ctimes',
    #    'oioioi.suspendjudge',
    #    'oioioi.submitsqueue',
    #    'oioioi.submitservice',
    #    'oioioi.timeline',
    #    'oioioi.amppz',
    #    'oioioi.balloons',
    #    'oioioi.statistics',
    #    'oioioi.publicsolutions',
    'oioioi.testspackages',
    #    'oioioi.pa',
    'oioioi.notifications',
    #    'oioioi.mailsubmit',
    'oioioi.portals',
    #    'oioioi.gamification',
    'oioioi.similarsubmits',
    'oioioi.disqualification',
    'oioioi.exportszu',
    'oioioi.globalmessage',
    'oioioi.newsfeed',
    'oioioi.simpleui',
    #    'yet_another_django_profiler',
    #    'oioioi.mainreportimporter',
    'oioioi.szkopul',
    'oioioi.problemsharing',
    'oioioi.usergroups',
    'oioioi.usercontests',
    'oioioi.plagiarism'
) + INSTALLED_APPS

PROBLEM_TAGS_VISIBLE = True

# Enables problem statistics at the cost of some per-submission performance hit.
# Set to True if you want to see statistics in the Problemset and problem sites.
# After enabling you should use ./manage.py recalculate_statistics
PROBLEM_STATISTICS_AVAILABLE = True

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    #    'oioioi.base.processors.gravatar',
    #    'oioioi.contestlogo.processors.logo_processor',
    #    'oioioi.contestlogo.processors.icon_processor',
    'oioioi.szkopul.processors.szkopul_contact',
    'oioioi.notifications.processors.notification_processor',
    #    'oioioi.gamification.processors.miniprofile_processor',
    'oioioi.globalmessage.processors.global_message_processor',
    'oioioi.portals.processors.portal_processor',
    'oioioi.portals.processors.portals_main_page_link_visible',
]

# VERY STUPID WORKAROUND FOR SZKOPUL-FK
if 'oioioi.problems.processors.dangling_problems_processor' in TEMPLATES[0]['OPTIONS']['context_processors']:
    TEMPLATES[0]['OPTIONS']['context_processors'].remove(
        'oioioi.problems.processors.dangling_problems_processor')
# AND FOR SZKOPUL-FJ
if 'oioioi.problems.processors.problems_need_rejudge_processor' in TEMPLATES[0]['OPTIONS']['context_processors']:
    TEMPLATES[0]['OPTIONS']['context_processors'].remove(
        'oioioi.problems.processors.problems_need_rejudge_processor')

AUTHENTICATION_BACKENDS += (
    'oioioi.teachers.auth.TeacherAuthBackend',
    #    'oioioi.ipdnsauth.backends.IpDnsBackend',
    'oioioi.usercontests.auth.UserContestAuthBackend',
)

# Limits the duration of user contests.
# Comment out if you don't want to limit the user contests duration.
USER_CONTEST_TIMEOUT = datetime(2020, 2, 7, 23, 0, 0, tzinfo=pytz.utc)

# Number of concurrently evaluated submissions (default is 1).
# EVALMGR_CONCURRENCY = 30
EVALMGR_CONCURRENCY = 10

# Number of concurrently processed problem packages (default is 1).
# UNPACKMGR_CONCURRENCY = 1

PROBLEM_SOURCES = PROBLEM_SOURCES + (
    'oioioi.sharingcli.problem_sources.RemoteSource',
    #    'oioioi.zeus.problem_sources.ZeusProblemSource',
)

# Cache
# To use the more efficient memcached, install it and uncomment the following:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# Notifications configuration (client)
# This one is for JavaScript WebSocket client.
# It should contain actual URL available from remote machines.
# NOTIFICATIONS_SERVER_URL = '//szkopul-notifications.dasie.mimuw.edu.pl/'
NOTIFICATIONS_SERVER_URL = '/'

# Notifications configuration (server)
NOTIFICATIONS_SERVER_ENABLED = True

# URL connection string to a Notifications Server instance
NOTIFICATIONS_OIOIOI_URL = 'https://szkopul.edu.pl/'

# URL connection string for RabbitMQ instance used by Notifications Server
NOTIFICATIONS_RABBITMQ_URL = 'amqp://localhost'

# Port that the Notifications Server listens on
NOTIFICATIONS_SERVER_PORT = 7887

SZKOPUL_SUPPORT_EMAIL = 'szkopul@fri.edu.pl'

CELERY_RESULT_BACKEND = None

# logging

# handled by sentry
MAIL_ADMINS_ON_GRADING_ERROR = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
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
        'console-dbg': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'date_and_level',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'audit': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'date_and_level',
            'filename': '/sio2/deployment/logs/audit.log'
        },
        'emit_notification': {
            'level': 'DEBUG',
            'class': 'oioioi.base.notification.NotificationHandler'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False
        },
        'oioioi': {
            'handlers': ['console', 'emit_notification'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'oioioi.workers.management.commands': {
            'handlers': ['console-dbg', 'emit_notification'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'oioioi.base.registration_backend.audit': {
            'handlers': ['console', 'audit'],
            'level': 'INFO',
            'propagate': False,
        },
        'oioioi.base.models.audit': {
            'handlers': ['console', 'audit'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

# If set to True, usercontests will become read-only: it will be impossible to
# change, delete or submit to existing usercontests, as well as add new ones
# This operation is fully reversible.
ARCHIVE_USERCONTESTS = True

# Experimental
USE_ACE_EDITOR = True
