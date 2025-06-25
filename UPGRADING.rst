================
Upgrading OIOIOI
================

Make sure you are in the *deployment* folder and the virtualenv is activated.
Then run::

  pip install -e git://github.com/sio2project/oioioi.git#egg=oioioi
  ./manage.py migrate
  ./manage.py collectstatic
  ./manage.py supervisor restart all

and restart the judging machines.

Fast Django Migration to 5.2 (Important for Large OIOIOI Instances)
-----------------------------------

The following migrations require removing an index (created by the deprecated ``index_together``) and creating a new one:

* ``oi/migrations/0008_sync_indexes_state.py``
* ``forum/migrations/0013_sync_indexes_state.py``
* ``contests/migrations/0021_sync_indexes_state.py``

Since dropping and then creating an index takes a long time for instances with a very large number of submissions, you can speed this up as follows:

Because these indexes are in the database schema, you should mark these migrations (``0008_sync_indexes_state.py``, ``0021_sync_indexes_state.py``, ``0013_sync_indexes_state.py``) as fake.
See the `django docs <https://docs.djangoproject.com/en/5.2/ref/django-admin/#cmdoption-migrate-fake>`_ for details.
Then, rename the existing indexes created by ``IndexTogether`` to the corresponding names specified in these migrations.
You can manually identify the indexes by checking which two fields they cover.

For example, an index named ``forum_post_thread_id_add_date_6d8ec21d_idx`` should be renamed to ``forum_post_thread__54acb8_idx``.
Similarly, rename the other indexes so that the database state is correct, i.e., the database contains indexes with the names specified in the migrations.

After these steps, you will achieve a consistent database state without waiting a long time for the migrations to complete.

::

    python manage.py migrate oi 0008 --fake

    python manage.py migrate forum 0021 --fake

    python manage.py migrate contests 0013 --fake

Changes in the deployment directory
-----------------------------------

When new features are added, the configuration files in your custom
*deployment* directory may need an update. An example valid configuration can
always be found in the *oioioi* sources
(*oioioi/deployment* directory, *\*.template* files).
One of the simplest ways to learn about the changes is::

    diff -u path_to_deployment/changed_file path_to_oioioi/oioioi/deployment/changed_file.template

Once you have made sure that your deployment
directory is up-to-date, change *CONFIG_VERSION* in your custom
*deployment/settings.py* so that it equals *INSTALLATION_CONFIG_VERSION* in
*oioioi/default_settings.py*.

List of changes since the *CONFIG_VERSION* numbering was introduced:

#. * Added *unpackmgr* queue entry to *deployment/supervisord.conf*::

       [program:unpackmgr]
       command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q unpackmgr -c {{ settings.UNPACKMGR_CONCURRENCY }}
       startretries=0
       stopwaitsecs=15
       redirect_stderr=true
       stdout_logfile={{ PROJECT_DIR }}/logs/unpackmgr.log

   * Added *USE_SINOLPACK_MAKEFILES* and *UNPACKMGR_CONCURRENCY*
     options to *deployment/settings.py*::

       USE_SINOLPACK_MAKEFILES = False
       #UNPACKMGR_CONCURRENCY = 1

#. * Added *Notifications Server* entries to *deployment/supervisord.conf*::

        [program:notifications-server]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py notifications_server
        redirect_stderr=true
        {% if not settings.NOTIFICATIONS_SERVER_ENABLED %}exclude=true{% endif %}

   * Added *NOTIFICATIONS_* options to *deployment/settings.py*::

        # Notifications configuration (client)
        # This one is for JavaScript WebSocket client.
        # It should contain actual URL available from remote machines.
        NOTIFICATIONS_SERVER_URL = 'http://localhost:7887/'

        # Notifications configuration (server)
        NOTIFICATIONS_SERVER_ENABLED = False

        # URL connection string to a Notifications Server instance
        NOTIFICATIONS_OIOIOI_URL = 'http://localhost:8000/'

        # URL connection string for RabbitMQ instance used by Notifications Server
        NOTIFICATIONS_RABBITMQ_URL = 'amqp://localhost'

        # Port that the Notifications Server listens on
        NOTIFICATIONS_SERVER_PORT = 7887

#. * Added *prizesmgr* queue entry to *deployment/supervisord.conf*::

       [program:prizesmgr]
       command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q prizesmgr -c 1
       startretries=0
       stopwaitsecs=15
       redirect_stderr=true
       stdout_logfile={{ PROJECT_DIR }}/logs/prizesmgr.log

#. * Added *ATOMIC_REQUESTS* database option to *deployment/settings.py*::

       DATABASES = {
        'default': {
         'ENGINE': 'django.db.backends.', # Add 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
         'NAME': '',                      # Or path to database file if using sqlite3.
         'USER': '',                      # Not used with sqlite3.
         'PASSWORD': '',                  # Not used with sqlite3.
         'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
         'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
         'ATOMIC_REQUESTS': True,         # Don't touch unless you know what you're doing.
        }
       }

#. * Added *rankingsd*, *cleanupd*, *ipauthsyncd*, *ipauth-dnsserver* entries
     to *deployment/supervisord.conf*::

        [program:rankingsd]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py rankingsd
        startretries=0
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/rankingsd.log

        [program:cleanupd]
        command={{ PROJECT_DIR }}/manage.py cleanupd
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/cleanupd.log

        [program:ipauthsyncd]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py ipauthsyncd
        startretries=0
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/ipauthsyncd.log
        {% if not 'oioioi.ipauthsync' in settings.INSTALLED_APPS %}exclude=true{% endif %}

        [program:ipauth-dnsserver]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py ipauth-dnsserver
        startretries=0
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/ipauth-dnsserver.log
        {% if not settings.IPAUTH_DNSSERVER_DOMAIN %}exclude=true{% endif %}

#. * Added new condition to *sioworkersd* in *deployment/supervisord.conf*
     and corresponding entry in *deployment/settings.py*::

        {% if settings.SIOWORKERS_BACKEND != 'oioioi.sioworkers.backends.SioworkersdBackend' or not settings.RUN_SIOWORKERSD %}exclude=true{% endif %}

#. * Added *evalmgr-zeus* entry
     to *deployment/supervisord.conf*::

        [program:evalmgr-zeus]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l debug -Q evalmgr-zeus -c 1
        startretries=0
        stopwaitsecs=15
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/evalmgr-zeus.log
        {% if not settings.ZEUS_INSTANCES %}exclude=true{% endif %}

   * Deleted *zeus-fetcher* entry from *deployment/supervisord.conf*.

   * Added *ZEUS_PUSH_GRADE_CALLBACK_URL* entry to *deployment/settings.py*::

        ZEUS_PUSH_GRADE_CALLBACK_URL = 'https://sio2.dasie.mimuw.edu.pl'

   * Added logging to file for logger *oioioi.zeus* in
     *deployment/settings.py*::

        LOGGING['handlers']['zeus_file'] = {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '__DIR__/logs/zeus.log',
            'maxBytes': 1024 * 1024 * 5, # 50 MB same as default in supervisord
            'backupCount': 10, # same as in supervisord
            'formatter': 'date_and_level',
        }
        LOGGING['loggers']['oioioi.zeus'] = {
            'handlers': ['zeus_file'],
            'level': 'DEBUG',
        }

#. * Removed *SAFE_EXEC_MODE* entry from *deployment/settings.py*.

#. * Removed *FILELOCK_BASEDIR* entry from *deployment/settings.py*.

#. * Removed *ENABLE_SPLITEVAL* and *SPLITEVAL_EVALMGR* entries from
     *deployment/settings.py*.

   * Removed *evalmgr-lowprio* entry from *deployment/supervisord.conf*.

#. * New version of sioworkers with changed database backend. Please update
     sioworkers with::

        . venv/bin/activate
        pip install -r requirements.txt

     and remove old database file (*deployment/sioworkersd.sqlite* by default).

   * Changed database filename (*--database* option) in
     *deployment/supervisord.conf*::

        [program:sioworkersd]
        command=twistd -n -l- --pidfile={{ PROJECT_DIR }}/pidfiles/sioworkersd.pid sioworkersd --database={{ PROJECT_DIR }}/sioworkersd.db
        # (...)

#. * Added commented out *OIOIOI_INSTANCE_PRIORITY_BONUS* and
     *OIOIOI_INSTANCE_WEIGHT_BONUS* entries to *deployment/settings.py*::

        # Bonus to judging priority ang judging weight for each contest on this
        # OIOIOI instance.
        #OIOIOI_INSTANCE_PRIORITY_BONUS = 0
        #OIOIOI_INSTANCE_WEIGHT_BONUS = 0

   * Modified comment to *SITE_NAME* entry in *deployment/settings.py*::

        # Site name displayed in the title and used by sioworkersd
        # to distinguish OIOIOI instances.
        SITE_NAME = 'OIOIOI'

#. * Removed *CeleryBackend* from sioworkers backends, *SioworkersdBackend*
     set as new default backend. Removed *[program:sioworkers]* entry from
     *deployment/supervisord.conf*.

#. * Added *PUBLIC_ROOT_URL* to *deployment/settings.py*::

        # The website address as it will be displayed to users in some places,
        # including but not limited to the mail notifications.
        # Defaults to 'http://localhost'.
        #PUBLIC_ROOT_URL = 'http://enter-your-domain-name-here.com'

    * Added `mailnotifyd`, a backend for handling e-mail subscription to
      *deployment/supervisord.conf*::

        [program:mailnotifyd]
        command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py mailnotifyd
        startretries=0
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/mailnotifyd.log

#. * Removed *SUBMITTABLE_EXTENSIONS* from *deployment/settings.py*.

#. * If you want to use Sentry (crash reporting and aggregation platform) you
     need to:

     * Correctly setup RAVEN_CONFIG (https://docs.sentry.io/quickstart/ should
       help you)::

         # Error reporting
         import raven

         RAVEN_CONFIG = {
             # Won't do anything with no dsn
             # tip: append ?timeout=5 to avoid dropouts during high reporting traffic
             'dsn': 'enter_your_dsn_here',
             # This should be a path to git repo
             'release': raven.fetch_git_sha(
                 os.path.join(os.path.dirname(oioioi.__file__), os.pardir)),
         }

     * Add new filter to the logging configuration::

         'filters': {
             ...
             'omit_sentry': {
                 '()': 'oioioi.base.utils.log.OmitSentryFilter'
             },
         }

     * Add Sentry handler::

         'handlers': {
             ...
             'sentry': {
                 'level': 'ERROR',
                 'filters': ['omit_sentry'],
                 'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
             }
         }

     * Add Sentry handler to every logger::

         'handlers': ['console', 'sentry'],

     * Add new loggers::

         'loggers': {
             ...
             'raven': {
                 'handlers': ['console', 'mail_admins'],
                 'level': 'DEBUG',
                 'propagate': False,
             },
             'sentry.errors': {
                 'handlers': ['console', 'mail_admins'],
                 'level': 'DEBUG',
                 'propagate': False,
             }
         }

#. * Upgrade to django 1.9 requires following changes in the config file

     * TEMPLATE_* variables got replaced with TEMPLATE array.
       TEMPLATE_CONTEXT_PROCESSORS should be changed to::

        TEMPLATES[0]['OPTIONS']['context_processors'] += [
        #    'oioioi.contestlogo.processors.logo_processor',
        #    'oioioi.contestlogo.processors.icon_processor',
        #    'oioioi.avatar.processors.gravatar',
        #    'oioioi.notifications.processors.notification_processor',
        #    'oioioi.globalmessage.processors.global_message_processor',
        ]

    * Settings should now declare an explicit SITE_ID, you can check your
      site id via management console::

        $ ./manage.py shell
        >>> Site.objects.get().id
        1

      The returned id should be added to your config file::

        SITE_ID = 1

#. * Added *filetracker-cache-cleaner* entry
     to *deployment/supervisord.conf*::

        [program:filetracker-cache-cleaner]
        command=filetracker-cache-cleaner -c {{ FILETRACKER_CACHE_ROOT }} -s {{ FILETRACKER_CACHE_SIZE }} -i {{ FILETRACKER_CACHE_CLEANER_SCAN_INTERVAL }} -p {{ FILETRACKER_CACHE_CLEANER_CLEAN_LEVEL }}
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/filetracker-cache-cleaner.log
        {% if not settings.FILETRACKER_CACHE_CLEANER_ENABLED %}exclude=true{% endif %}

    * Added new options related to *remote_storage_factory* to
      *deployment/settings.py*::

        # When using a remote_storage_factory it's necessary to specify a cache
        # directory in which necessary files will be stored.
        #FILETRACKER_CACHE_ROOT = '__DIR__/cache'

        # When using a remote storage it's recommended to enable a cache cleaner deamon
        # which will periodically scan cache directory and remove files what aren't
        # used. For a detailed description of each option, please read a cache cleaner
        # configuration section in the sioworkersd documentation.
        #FILETRACKER_CACHE_CLEANER_ENABLED = True
        #FILETRACKER_CACHE_CLEANER_SCAN_INTERVAL = '1h'
        #FILETRACKER_CACHE_CLEANER_CLEAN_LEVEL = '50'
        #FILETRACKER_CACHE_SIZE = '8G'

#. * Added *oioioiworker* entry
     to *deployment/supervisord.conf*::

        [program:oioioiworker]
        command=twistd -n -l- --pidfile={{ PROJECT_DIR }}/pidfiles/oioioiworker.pid worker -c 2 localhost
        redirect_stderr=true
        stdout_logfile={{ PROJECT_DIR }}/logs/oioioiworker.log
        {% if not settings.RUN_LOCAL_WORKERS %}exclude=true{% endif %}

     so that the flag RUN_LOCAL_WORKERS has the desirable effect.

#. * Enabled *oioioi.workers* app by default to fix *receive_from_workers*
     crashes.

   * Made *oioioi.prizes* Celery configuration conditional on this app being
     installed. This prevents *evalmgr* and *unpackmgr* crashes caused by assuming
     that *oioioi.prizes* is always enabled.

#. * Applied the following patch to *deployment/settings.py*::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -119,10 +119,16 @@ SEND_USER_ACTIVATION_EMAIL = False
         # the given port will be able to see all the files. It's recommended to have
         # the judging machines on a separate physical network and listen only on the
         # corresponding IP address.
        -#FILETRACKER_SERVER_ENABLED = True
         #FILETRACKER_LISTEN_ADDR = '0.0.0.0'
        +
        +# Uncomment and change this to run filetracker on non-default port.
         #FILETRACKER_LISTEN_PORT = 9999

         # When using a remote_storage_factory it's necessary to specify a cache
         # directory in which a necessary files will be stored.
         #FILETRACKER_CACHE_ROOT = '__DIR__/cache'

#. * Enabled use of caching template loaders when *settings.DEBUG* is set to *False*
     to turn on a cache of compiled templates in production environment.

   * Set *APP_DIRS* option to *False* to fix the "either remove APP_DIRS or remove the 'loaders'
     option" crashes::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -14,7 +14,13 @@ DEBUG = True

         if DEBUG:
             TEMPLATES[0]['OPTIONS']['loaders'] = UNCACHED_TEMPLATE_LOADERS
        -    TEMPLATES[0]['APP_DIRS'] = False
        +else:
        +    # Cache compiled templates in production environment.
        +    TEMPLATES[0]['OPTIONS']['loaders'] = CACHED_TEMPLATE_LOADERS
        +
        +# The APP_DIRS option is allowed only in template engines that have no custom
        +# loaders specified.
        +TEMPLATES[0]['APP_DIRS'] = False

#. * Removed the FILETRACKER_CLIENT_FACTORY setting, because media_root_factory
     will not be compatible with filetracker 2.x.
     If you use it, you should move to remote_storage_factory before upgrading the filetracker,
     which has become the default setting.

   * Also updated the URL with changes in the deployment directory::

        diff --git a/oioioi/deployment/settings.py.template b/oioioi/deployment/settings.py.template
        index 92b4a4e5..851beada 100755
        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -4,7 +4,7 @@ import os.path
         # This should match INSTALLATION_CONFIG_VERSION in
         # "oioioi/default_settings.py".
         # Before you adjust it, you may consider visiting
        -# "https://github.com/sio2project/oioioi/#changes-in-the-deployment-directory".
        +# "https://github.com/sio2project/oioioi/blob/master/UPGRADING.rst#changes-in-the-deployment-directory".
         CONFIG_VERSION = __CONFIG_VERSION__

         # Enable debugging features.
        @@ -108,17 +108,6 @@ SEND_USER_ACTIVATION_EMAIL = False
         # but this is unreliable and not intended for production.
         #BROKER_URL = 'amqp://guest:guest@localhost:5672//'

        -# Filetracker server settings.
        -#
        -# Determines which filetracker database use, availible options are:
        -# - 'oioioi.filetracker.client.media_root_factory' (the default)
        -#    Stores files on local filesystem under MEDIA_ROOT, optionally
        -#    exposing them with a filetracker server (see section below).
        -# - 'oioioi.filetracker.client.remote_storage_factory'
        -#    Connects to a filetracker server at FILETRACKER_URL, uses a local
        -#    cache with recently used files under CACHE_ROOT directory.
        -#FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.media_root_factory'
        -


#. * Uncommented `FILETRACKER_CACHE_ROOT` which is required by `remote_storage_factory`::

        diff --git a/oioioi/deployment/settings.py.template b/oioioi/deployment/settings.py.template
        index 851beada..11ce79a8 100755
        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -124,9 +124,10 @@ SEND_USER_ACTIVATION_EMAIL = False
        # this also defines the filetracker server oioioi should connect to.
        #FILETRACKER_URL = 'http://127.0.0.1:9999'

        -# When using a remote_storage_factory it's necessary to specify a cache
        -# directory in which a necessary files will be stored.
        -#FILETRACKER_CACHE_ROOT = '__DIR__/cache'
        +# When using a remote_storage_factory (it's the default storage factory)
        +# it's necessary to specify a cache directory
        +# in which the necessary files will be stored.
        +FILETRACKER_CACHE_ROOT = '__DIR__/cache'


#. * Filetracker server doesn't support default `-L /dev/stderr` option anymore:
     the argument to `-L` must be an actual seekable file. If you reconfigured
     `-L` to use a file, there is no need to change anything. If you used the
     default `supervisord.conf`, you should remove the `-L` flag: logs are now
     printed to stdout by default, and supervisord redirects stderr to stdout.


#. * Added `'oioioi.portals.processors.portals_main_page_link_visible'`, to
     `TEMPLATES[0]['OPTIONS']['context_processors']`::

        --- oioioi/deployment/settings.py.template	(date 1524038411000)
        +++ oioioi/deployment/settings.py.template	(date 1528164979000)
        @@ -333,6 +333,7 @@
         #    'oioioi.notifications.processors.notification_processor',
         #    'oioioi.globalmessage.processors.global_message_processor',
         #    'oioioi.portals.processors.portal_processor',
        +#    'oioioi.portals.processors.portals_main_page_link_visible',
         ]

         MIDDLEWARE_CLASSES += (


#. * Changed error (stderr) logging for processes spawned by supervisor. Now each process
     has its own log file. Changes to *deployment/supervisord.conf*::

        For each [program:A] entry change redirect_stderr=true to redirect_stderr=false and
        add the following line (where A is the name of process):
        stderr_logfile={{ PROJECT_DIR }}/logs/A-err.log

        Additionally in [program:notifications-server] add the following line:
        stdout_logfile={{ PROJECT_DIR }}/logs/notifications-server.log
        stderr_logfile={{ PROJECT_DIR }}/logs/notifications-server-err.log

        In [program:autoreload] add the following lines:
        redirect_stderr=false
        stdout_logfile={{ PROJECT_DIR }}/logs/autoreload.log
        stderr_logfile={{ PROJECT_DIR }}/logs/autoreload-err.log


#. * Added `DEFAULT_SAFE_EXECUTION_MODE` to Django settings with default of
     `"vcpu"` - OITimeTool.::

        diff --git a/oioioi/deployment/settings.py.template b/oioioi/deployment/settings.py.template
        index ea64d434..50c178b6 100755
        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -213,6 +213,12 @@ RUN_LOCAL_WORKERS = True
         USE_UNSAFE_EXEC = True
         USE_LOCAL_COMPILERS = True

        +# Default safe execution sandbox
        +# You can change the safe execution sandbox. Current options are:
        +# - "vcpu" - OITimeTool
        +# - "sio2jail" - SIO2Jail
        +#DEFAULT_SAFE_EXECUTION_MODE = "vcpu"
        +
         # WARNING: setting this to False is experimental until we make sure that
         # checkers do work well in sandbox
         #


#. * Added `PROBLEM_STATISTICS_AVAILABLE` to settings (`False` by default).::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -321,6 +321,11 @@ PROBLEMSET_LINK_VISIBLE = True
         # Comment out to show tags on the list of problems
         #PROBLEM_TAGS_VISIBLE = True

        +# Enables problem statistics at the cost of some per-submission performance hit.
        +# Set to True if you want to see statistics in the Problemset and problem sites.
        +# After enabling you should use ./manage.py recalculate_statistics
        +#PROBLEM_STATISTICS_AVAILABLE = True
        +
         # Set to True to allow every logged in user to add problems directly to Problemset
         EVERYBODY_CAN_ADD_TO_PROBLEMSET = False

#. * Added `NOTIFICATIONS_RABBITMQ_EXTRA_PARAMS` to settings::

       --- a/oioioi/deployment/settings.py.template
       +++ b/oioioi/deployment/settings.py.template
       @@ -400,6 +400,12 @@ ZEUS_INSTANCES = {
        # URL connection string for RabbitMQ instance used by Notifications Server
        #NOTIFICATIONS_RABBITMQ_URL = 'amqp://localhost'

       +# Extra arguments for pika ConnectionParameters, see
       +# https://pika.readthedocs.io/en/stable/modules/parameters.html
       +#NOTIFICATIONS_RABBITMQ_EXTRA_PARAMS = {
       +#    'heartbeat': 8
       +#}
       +
        # Port that the Notifications Server listens on
        #NOTIFICATIONS_SERVER_PORT = 7887

#. * Changed middleware classes' style to the new one (Django 1.10).::

        Move all middlewares from MIDDLEWARE_CLASSES to MIDDLEWARE in settings.py.
        Simply rename MIDDLEWARE_CLASSES settings variable to MIDDLEWARE.

#. * Added ``oioioi.problemsharing`` module. *We suggest enabling if oioioi.teachers module is used*.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -306,6 +306,7 @@ INSTALLED_APPS = (
         #    'oioioi.portals',
         #    'oioioi.globalmessage',
         #    'oioioi.newsfeed',
        +#    'oioioi.problemsharing',
         ) + INSTALLED_APPS

         # Additional Celery configuration necessary for 'prizes' app.

#. * Added ``oioioi.usergroups`` module.::

        Add the following line at the end of your INSTALLED_APPS variable
        in settings.py (if you want to use the new app simply uncomment this line):

        #    'oioioi.usergroups',

#. * Introduced `DEFAULT_COMPILERS` to settings, which should be set for every language supoorted::

        --- a/oioioi/default_settings.py
        +++ b/oioioi/default_settings.py
        @@ -15,7 +15,7 @@ from oioioi.contests.current_contest import ContestMode

         from django.contrib.messages import constants as messages

         DEBUG = False
         INTERNAL_IPS = ('127.0.0.1',)
        @@ -302,6 +302,12 @@ USE_LOCAL_COMPILERS = False
         DEFAULT_SAFE_EXECUTION_MODE = "vcpu"
         RUN_LOCAL_WORKERS = False

        +# This setting sets the default compilers used throughout the platform.
        +# There should be an entry for every language supported with key being the same
        +# as in SUBMITTABLE_EXTENSIONS
        +DEFAULT_COMPILERS = {'C': 'gcc', 'C++': 'gcc', 'Pascal': 'fpc', 'Java': 'java',
        +                     'Python': 'gcc'}
        +
         # WARNING: experimental, see settings template
         USE_UNSAFE_CHECKER = True

#. * Introduced `AVAILABLE_COMPILERS` to settings, which should be set to compilers available in sioworkers for every language supported.::

        +# This setting specifies which compilers are available in sioworkers
        +AVAILABLE_COMPILERS = {
        +        'C': ['gcc'],
        +        'C++': ['g++'],
        +        'Pascal': ['fpc'],
        +        'Java': ['Java'],
        +        'Python': ['Python']
        +}
        +

#. * Added option to block uploading HTML problem statements in sinol packages
     by untrusted users.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -251,6 +251,14 @@ USE_LOCAL_COMPILERS = True
         # execution (in a sandboxed environment, if USE_UNSAFE_EXEC is set to False).
         USE_SINOLPACK_MAKEFILES = False

        +# When set to True untrusted users cannot upload sinol packages containing
        +# problem statement in HTML format (they must use PDF).
        +# Trusted users are users with superuser access or teachers (if oioioi.teachers
        +# app is enabled). This option has no effect for packages uploaded
        +# by management commands or if USE_SINOLPACK_MAKEFILES is enabled.
        +# We suggest enabling it when using oioioi.usercontests app.
        +SINOLPACK_RESTRICT_HTML = False
        +
         # Scorers below are used for judging submissions without contests,
         # eg. submitting to problems from problemset.
         # DEFAULT_TEST_SCORER = \

#. * Added ``oioioi.usercontests`` module.::

        Add the following (commented out) line to the INSTALLED_APPS variable in
        settings.py:

        #    'oioioi.usercontests',

        Add the following (commented out) line to the AUTHENTICATION_BACKENDS
        variable in settings.py:

        #    'oioioi.usercontests.auth.UserContestAuthBackend',

#. * Added the `ARCHIVE_USERCONTESTS` setting.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -457,3 +457,6 @@ RAVEN_CONFIG = {
         # OIOIOI instance.
         #OIOIOI_INSTANCE_PRIORITY_BONUS = 0
         #OIOIOI_INSTANCE_WEIGHT_BONUS = 0
        +
        +# If set to True, usercontests will become read-only: it will be impossible to
        +# change, delete or submit to existing usercontests, as well as add new ones.
        +# This operation is fully reversible.
        +#ARCHIVE_USERCONTESTS = True

#. * Removed ``oioioi.jotform`` module. ``JOTFORM_ID`` can be removed
     from ``settings.py``. There is no need to modify other variables,
     as the module was enabled by default.

#. * Removed ``oioioi.prizes`` module. If you like you may remove ``prizes_*`` tables
     from database but it's not strictly necessary.
     Apart from ``settings.py`` the ``supervisord.conf`` should be updated::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -325,7 +325,6 @@ INSTALLED_APPS = (
         #    'oioioi.testspackages',
         #    'oioioi.pa',
         #    'oioioi.notifications',
        -#    'oioioi.prizes',
         #    'oioioi.mailsubmit',
         #    'oioioi.portals',
         #    'oioioi.globalmessage',
        @@ -335,13 +334,6 @@ INSTALLED_APPS = (
         #    'oioioi.usercontests',
         ) + INSTALLED_APPS

        -# Additional Celery configuration necessary for 'prizes' app.
        -if 'oioioi.prizes' in INSTALLED_APPS:
        -    CELERY_IMPORTS.append('oioioi.prizes.models')
        -    CELERY_ROUTES.update({
        -        'oioioi.prizes.models.prizesmgr_job': dict(queue='prizesmgr'),
        -    })
        -
         # Set to True to show the link to the problemset with contests on navbar.
         PROBLEMSET_LINK_VISIBLE = True

        --- a/oioioi/deployment/supervisord.conf.template
        +++ b/oioioi/deployment/supervisord.conf.template
        @@ -65,15 +65,6 @@ stdout_logfile={{ PROJECT_DIR }}/logs/evalmgr-zeus.log
         stderr_logfile={{ PROJECT_DIR }}/logs/evalmgr-zeus-err.log
         {% if not settings.ZEUS_INSTANCES %}exclude=true{% endif %}

        -[program:prizesmgr]
        -command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q prizesmgr -c 1
        -startretries=0
        -stopwaitsecs=15
        -redirect_stderr=false
        -stdout_logfile={{ PROJECT_DIR }}/logs/prizesmgr.log
        -stderr_logfile={{ PROJECT_DIR }}/logs/prizesmgr-err.log
        -{% if 'oioioi.prizes' not in settings.INSTALLED_APPS %}exclude=true{% endif %}
        -
         [program:filetracker-server]
         command=filetracker-server -d {{ settings.MEDIA_ROOT }} -l {{ settings.FILETRACKER_LISTEN_ADDR }} -p {{ settings.FILETRACKER_LISTEN_PORT }} -D
         redirect_stderr=false

#. * Changed default compilers. Added the display_name property to each compiler.
     This property is responsible for the compiler name, that users see in the
     submit view of a programming problem.
     Deleted the USE_LOCAL_COMPILERS setting, configure the AVAILABLE_COMPILERS
     setting instead to use system compilers, if that's your preference.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -171,22 +171,6 @@ LOGGING['loggers']['oioioi.zeus'] = {
         # because you use instance started by another instance of OIOIOI)
         #RUN_SIOWORKERSD = True

        -# This setting specifies which compilers are available in sioworkers.
        -# By default that means ones defined here:
        -# https://github.com/sio2project/sioworkers/blob/master/setup.py#L71
        -#AVAILABLE_COMPILERS = {
        -#        'C': ['c'],
        -#        'C++': ['cpp'],
        -#        'Pascal': ['pas'],
        -#        'Java': ['java'],
        -#        'Python': ['py']
        -#}
        -
        -# This setting sets the default compilers used throughout the platform.
        -# By uncommenting the below dict you can change all or any one of them.
        -#DEFAULT_COMPILERS = {'C': 'c', 'C++': 'cpp', 'Pascal': 'pas', 'Java': 'java',
        -#                     'Python': 'py'}
        -
         # Contest mode - automatic activation of contests.
         #
         # Available choices are:
        @@ -227,7 +211,58 @@ RUN_LOCAL_WORKERS = True
         # Before this only system compilers can be used and the safe execution
         # supervisor is not available.
         USE_UNSAFE_EXEC = True
        -USE_LOCAL_COMPILERS = True
        +SYSTEM_COMPILERS = {
        +    'C': {
        +        'system-gcc': {'display_name': 'system gcc'}
        +    },
        +    'C++': {
        +        'system-g++': {'display_name': 'system g++'}
        +    },
        +    'Pascal': {
        +        'system-fpc': {'display_name': 'system fpc'}
        +    },
        +    'Java': {
        +        'system-java': {'display_name': 'system java'}
        +    },
        +    'Python': {
        +        'system-python': {'display_name': 'system python'}
        +    }
        +}
        +AVAILABLE_COMPILERS = SYSTEM_COMPILERS
        +SYSTEM_DEFAULT_COMPILERS = {'C': 'system-gcc', 'C++': 'system-g++',
        +                     'Pascal': 'system-fpc', 'Java': 'system-java',
        +                     'Python': 'system-python'}
        +DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS
        +
        +# This setting specifies which compilers are available in sioworkers.
        +# By default that means the ones defined here:
        +# https://github.com/sio2project/sioworkers/blob/master/setup.py#L71
        +# By uncommenting the below dict you can change all or any one of them.
        +# Each compiler must contain a display_name entry.
        +#AVAILABLE_COMPILERS = {
        +#    'C': {
        +#        'gcc4_8_2_c99': {'display_name': 'gcc:4.8.2 std=gnu99'}
        +#    },
        +#    'C++': {
        +#        'g++4_8_2_cpp11': {'display_name': 'g++:4.8.2 std=c++11'}
        +#    },
        +#    'Pascal': {
        +#        'fpc2_6_2': {'display_name': 'fpc:2.6.2'}
        +#    },
        +#    'Java': {
        +#        'java1_8': {'display_name': 'java:1.8'}
        +#    },
        +#    'Python': {
        +#        'python': {'display_name': 'python'}
        +#    }
        +#}
        +
        +# This setting sets the default compilers used throughout the platform.
        +# By uncommenting the below dict you can change all or any one of them.
        +#DEFAULT_COMPILERS = {'C': 'gcc4_8_2_c99', 'C++': 'g++4_8_2_cpp11',
        +#                     'Pascal': 'fpc2_6_2', 'Java': 'java1_8',
        +#                     'Python': 'python'}

#. * Added the 'USER_CONTEST_TIMEOUT' setting for limiting user contest duration.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -405,6 +405,12 @@ AUTHENTICATION_BACKENDS += (
         #    'oioioi.ipdnsauth.backends.IpDnsBackend',
         )

        +# Limits the duration of user contests.
        +# Comment out if you don't want to limit the user contests duration.
        +#import pytz
        +#from datetime import datetime
        +#USER_CONTEST_TIMEOUT = datetime(2020, 2, 7, 23, 0, 0, tzinfo=pytz.utc)
        +
         # Number of concurrently evaluated submissions (default is 1).
         #EVALMGR_CONCURRENCY = 30

#. * Removed 'celerycam' and 'cleanupd' from the list of supervisor programs.
     Updated celery worker startup commands.::

        --- a/oioioi/deployment/supervisord.conf.template
        +++ b/oioioi/deployment/supervisord.conf.template
        @@ -19,13 +19,6 @@ stdout_logfile={{ PROJECT_DIR }}/logs/uwsgi.log
         stderr_logfile={{ PROJECT_DIR }}/logs/uwsgi-err.log
         {% if settings.UWSGI_ENABLED == False %}exclude=true{% elif settings.UWSGI_ENABLED == 'auto' and settings.DEBUG %}exclude=true{% endif %}

        -[program:celerycam]
        -command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celerycam --pidfile={{ PROJECT_DIR }}/pidfiles/celerycam.pid
        -startretries=0
        -redirect_stderr=false
        -stdout_logfile={{ PROJECT_DIR }}/logs/celerycam.log
        -stderr_logfile={{ PROJECT_DIR }}/logs/celerycam-err.log
        -
         [program:rankingsd]
         command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py rankingsd
         startretries=0
        @@ -41,7 +34,7 @@ stdout_logfile={{ PROJECT_DIR }}/logs/mailnotifyd.log
         stderr_logfile={{ PROJECT_DIR }}/logs/mailnotifyd-err.log

         [program:unpackmgr]
        -command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q unpackmgr -c {{ settings.UNPACKMGR_CONCURRENCY }}
        +command=celery -A oioioi.celery worker -E -l info -Q unpackmgr -c {{ settings.UNPACKMGR_CONCURRENCY }}
         startretries=0
         stopwaitsecs=15
         redirect_stderr=false
        @@ -49,7 +42,7 @@ stdout_logfile={{ PROJECT_DIR }}/logs/unpackmgr.log
         stderr_logfile={{ PROJECT_DIR }}/logs/unpackmgr-err.log

         [program:evalmgr]
        -command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q evalmgr -c {{ settings.EVALMGR_CONCURRENCY }}
        +command=celery -A oioioi.celery worker -E -l info -Q evalmgr -c {{ settings.EVALMGR_CONCURRENCY }}
         startretries=0
         stopwaitsecs=15
         redirect_stderr=false
        @@ -57,7 +50,7 @@ stdout_logfile={{ PROJECT_DIR }}/logs/evalmgr.log
         stderr_logfile={{ PROJECT_DIR }}/logs/evalmgr-err.log

         [program:evalmgr-zeus]
        -command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py celeryd -E -l info -Q evalmgr-zeus -c 1
        +command=celery -A oioioi.celery worker -E -l info -Q evalmgr-zeus -c 1
         startretries=0
         stopwaitsecs=15
         redirect_stderr=false
        @@ -102,12 +95,6 @@ stdout_logfile={{ PROJECT_DIR }}/logs/sioworkersd.log
         stderr_logfile={{ PROJECT_DIR }}/logs/sioworkersd-err.log
         {% if settings.SIOWORKERS_BACKEND != 'oioioi.sioworkers.backends.SioworkersdBackend' or not settings.RUN_SIOWORKERSD %}exclude=true{% endif %}

        -[program:cleanupd]
        -command={{ PROJECT_DIR }}/manage.py cleanupd
        -redirect_stderr=false
        -stdout_logfile={{ PROJECT_DIR }}/logs/cleanupd.log
        -stderr_logfile={{ PROJECT_DIR }}/logs/cleanupd-err.log
        -
         [program:ipauthsyncd]
         command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py ipauthsyncd
         startretries=0

#. * Changed the 'UWSGI_ENABLED' setting to a more general 'SERVER' setting.
     To make sure that your typical production setup (UWSGI + reverse proxy)
     keeps working, set this to 'uwsgi'.::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -34,0 +38,6 @@
        +# The server to be run. Options are:
        +# 'django' - django's http server
        +# 'uwsgi' - uwsgi daemon
        +# 'uwsgi-http' - uwsgi deamon with built-in http server
        +# None - nothing will be run
        +SERVER = 'django'

   * Appropriate changes were also made to the supervisor configuration.::

        --- a/oioioi/deployment/supervisord.conf.template
        +++ b/oioioi/deployment/supervisord.conf.template
        @@ -7,17 +7,19 @@ directory={{ PROJECT_DIR }}
         identifier=oioioi-supervisor

         [program:uwsgi]
        -{% if settings.UWSGI_USE_GEVENT %}
        -command=uwsgi -s {{ PROJECT_DIR }}/uwsgi.sock --umask=000 --loop=gevent --async=50 --processes=10 -M --max-requests=5000 --disable-logging --need-app --enable-threads --socket-timeout=30 --wsgi-file={{ PROJECT_DIR }}/wsgi.py
        -{% else %}
        -command=uwsgi -s {{ PROJECT_DIR }}/uwsgi.sock --umask=000 --processes=10 -M --max-requests=5000 --disable-logging --need-app --enable-threads --socket-timeout=30 --wsgi-file={{ PROJECT_DIR }}/wsgi.py
        -{% endif %}
        +command=uwsgi {% if settings.SERVER == 'uwsgi-http' %}--http :8000 --static-map {{ settings.STATIC_URL }}={{ settings.STATIC_ROOT }} {% else %}-s {{ PROJECT_DIR }}/uwsgi.sock {% endif %}--umask=000 {% if settings.UWSGI_USE_GEVENT %}--loop=gevent --async=50 {% endif %}--processes=10 -M --max-requests=5000 --disable-logging --need-app --enable-threads --socket-timeout=30 --wsgi-file={{ PROJECT_DIR }}/wsgi.py
         stopsignal=INT
         startretries=0
         redirect_stderr=false
         stdout_logfile={{ PROJECT_DIR }}/logs/uwsgi.log
         stderr_logfile={{ PROJECT_DIR }}/logs/uwsgi-err.log
        -{% if settings.UWSGI_ENABLED == False %}exclude=true{% elif settings.UWSGI_ENABLED == 'auto' and settings.DEBUG %}exclude=true{% endif %}
        +{% if settings.SERVER|slice:":5" != 'uwsgi' %}exclude=true{% endif %}
        +
        +[program:django-http]
        +command={{ PYTHON }} {{ PROJECT_DIR }}//manage.py runserver 0.0.0.0:8000
        +stdout_logfile={{ PROJECT_DIR }}/logs/runserver/out.log
        +stderr_logfile={{ PROJECT_DIR }}/logs/runserver/err.log
        +{% if settings.SERVER != 'django' %}exclude=true{% endif %}

         [program:rankingsd]
         command={{ PYTHON }} {{ PROJECT_DIR }}/manage.py rankingsd

#. * Removed OITimeTool and changed 'DEFAULT_SAFE_EXECUTION_MODE' from 'vcpu' to 'sio2jail'.
     'vcpu' is no longer a viable safe execution option. Following changes have to be made
     to settings.py: ::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -258,8 +258,7 @@ USE_UNSAFE_EXEC = True

         # Default safe execution tool
         # You can change the safe execution tool. Current options are:
        -# - "vcpu" - (default) OITimeTool
        -# - "sio2jail" - SIO2Jail
        +# - "sio2jail" - (default) SIO2Jail
         # - "cpu" - ptrace (measures real time)
         #DEFAULT_SAFE_EXECUTION_MODE = "sio2jail"


#. * Added audio playback of captcha. Following changes have to be made
     to settings.py: ::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -479,3 +479,13 @@ ZEUS_INSTANCES = {
         # change, delete or submit to existing usercontests, as well as add new ones.
         # This operation is fully reversible.
         #ARCHIVE_USERCONTESTS = True
        +
        +# If set to locations of flite and sox executables, enables audio playback
        +# of captcha. Audio output generated by flite (CAPTCHA_FLITE_PATH) is identical
        +# for captchas with the same text. To prevent potential security risk,
        +# CAPTCHA_SOX_PATH should be set as well, in order to inject random noise into
        +# audio files  generated by flite. If either sox or flite is installed
        +# and is in PATH variable, then corresponding settings will be set automatically.
        +# CAPTCHA_FLITE_PATH = ''
        +# CAPTCHA_SOX_PATH = ''

#. * Removed avatar module. Gravatar processors is now in the base module: ::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -308,7 +308,6 @@ MAX_MEMORY_LIMIT_FOR_TEST = 256 * 1024

        INSTALLED_APPS = (
            'oioioi.contestlogo',
        -    'oioioi.avatar',
        #    'oioioi.teachers',
        #    'oioioi.simpleui',
        #    'oioioi.ipdnsauth',
        @@ -364,9 +363,9 @@ PROBLEMSET_LINK_VISIBLE = True
        EVERYBODY_CAN_ADD_TO_PROBLEMSET = False

        TEMPLATES[0]['OPTIONS']['context_processors'] += [
        +   'oioioi.base.processors.gravatar',
            'oioioi.contestlogo.processors.logo_processor',
            'oioioi.contestlogo.processors.icon_processor',
        -   'oioioi.avatar.processors.gravatar',
        #    'oioioi.notifications.processors.notification_processor',
            'oioioi.globalmessage.processors.global_message_processor',
        #    'oioioi.portals.processors.portal_processor',

#. * Added type key for languages and added "Output-only" language.: ::

        --- a/oioioi/default_settings.py
        +++ b/oioioi/default_settings.py
        @@ -14,7 +14,7 @@ from django.contrib.messages import constants as messages

        from django.utils.translation import gettext_lazy as _

        -INSTALLATION_CONFIG_VERSION = 47
        +INSTALLATION_CONFIG_VERSION = 48

        DEBUG = False
        INTERNAL_IPS = ('127.0.0.1',)
        @@ -318,9 +318,12 @@ SIOWORKERS_LISTEN_URL = None
        RUN_LOCAL_WORKERS = False

        # This setting specifies which languages are available on the platform.
        -# Each language must contain a diplay_name entry. Such an entry may be useful
        +# Each language must contain type and display_name entry. Such an entry may be useful
        # if it is to contain characters, that probably shouldn't be allowed in the
        -# language identifier, such as '#'.
        +# language identifier, such as '#'. Languages of type 'main'
        +# ('main' is default type, it doesn't need to be set)
        +# are enabled on every problem by default, languages of type 'extra'
        +# can only be enabled on a problem by adding them to the problems white list.
        SUBMITTABLE_LANGUAGES = {
            'C': {
                'display_name': 'C'
        @@ -336,6 +339,10 @@ SUBMITTABLE_LANGUAGES = {
            },
            'Python': {
                'display_name': 'Python'
        +    },
        +    'Output-only': {
        +        'type': 'extra',
        +        'display_name': 'Output-only',
            }
        }

        @@ -343,7 +350,7 @@ SUBMITTABLE_LANGUAGES = {
        # There should be an entry for every language supported with key being the same
        # as in SUBMITTABLE_LANGUAGES.
        SUBMITTABLE_EXTENSIONS = {'C': ['c'], 'C++': ['cpp', 'cc'], 'Pascal': ['pas'],
        -                          'Java': ['java'], 'Python': ['py']}
        +                          'Java': ['java'], 'Python': ['py'], 'Output-only': ['txt', 'out']}

        # This setting specifies which compilers are available in sioworkers.
        # By default that means ones defined here:
        @@ -366,6 +373,9 @@ AVAILABLE_COMPILERS = {
            },
            'Python': {
                'python': {'display_name': 'python'}
        +    },
        +    'Output-only': {
        +        'output-only': {'display_name': 'output-only'}
            }
        }

        @@ -384,6 +394,9 @@ SYSTEM_COMPILERS = {
            },
            'Python': {
                'system-python': {'display_name': 'system python'}
        +    },
        +    'Output-only': {
        +        'output-only': {'display_name': 'output-only'}
            }
        }

        @@ -392,11 +405,11 @@ SYSTEM_COMPILERS = {
        # as in SUBMITTABLE_LANGUAGES and value contained in AVAILABLE_COMPILERS.
        DEFAULT_COMPILERS = {'C': 'gcc4_8_2_c99', 'C++': 'g++4_8_2_cpp11',
                            'Pascal': 'fpc2_6_2', 'Java': 'java1_8',
        -                     'Python': 'python'}
        +                     'Python': 'python', 'Output-only': 'output-only'}

        SYSTEM_DEFAULT_COMPILERS = {'C': 'system-gcc', 'C++': 'system-g++',
                            'Pascal': 'system-fpc', 'Java': 'system-java',
        -                     'Python': 'system-python'}
        +                     'Python': 'system-python', 'Output-only': 'output-only'}

        USE_UNSAFE_EXEC = False
        DEFAULT_SAFE_EXECUTION_MODE = "sio2jail"

#. * Sentry client update from raven to sentry-sdk:
    * Apply change in wsgi.py: ::

        --- a/oioioi/deployment/wsgi.py.template
        +++ b/oioioi/deployment/wsgi.py.template     @@ -27,9 +27,8 @@ init_env('__DIR__')
        # This application object is used by any WSGI server configured to use this
        # file. This includes Django's development server, if the WSGI_APPLICATION
        # setting points here.
        -from raven.contrib.django.raven_compat.middleware.wsgi import Sentry
        from django.core.wsgi import get_wsgi_application
        -application = Sentry(get_wsgi_application())
        +application = get_wsgi_application()

    * Apply change in settings.py: ::

        --- a/oioioi/deployment/settings.py.template
        +++ b/oioioi/deployment/settings.py.template
        @@ -454,16 +454,23 @@ ZEUS_INSTANCES = {
         #IPAUTH_DNSSERVER_DOMAIN = 'oioioi.example.com'

         # Error reporting
        -# import raven
        +# import sentry_sdk
        +# from sentry_sdk.integrations.django import DjangoIntegration
         #
        -# RAVEN_CONFIG = {
        +# def filter_sentry(event, hint):
        +#     extra = event.get('extra', {})
        +#     if extra.get('omit_sentry', False):
        +#         return None
        +#     return event
        +#
        +#
        +# sentry_sdk.init(
         #     # Won't do anything with no dsn
         #     # tip: append ?timeout=5 to avoid dropouts during high reporting traffic
        -#     'dsn': '',
        -#     # This should be a path to git repo
        -#     'release': raven.fetch_git_sha(
        -#         os.path.join(os.path.dirname(oioioi.__file__), os.pardir)),
        -# }
        +#     dsn='',
        +#     integrations=[DjangoIntegration()],
        +#     before_send=filter_sentry,
        +# )

     * Remove all sentry and raven reminiscent from settings.py in LOGGING SECTION.
