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

Upgrading from django 1.8
~~~~~~~~~~~~~~~~~~~~~~~~~
Please make sure to reinstall all packages to avoid compatibility issues::

  pip install -e git://github.com/sio2project/oioioi.git#egg=oioioi
  pip install -I --force-reinstall -r requirements.txt
  ./manage.py migrate
  ./manage.py collectstatic
  ./manage.py supervisor restart all

Changes in the deployment directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
        # This one is for JavaScript socket.io client.
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
         'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
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


