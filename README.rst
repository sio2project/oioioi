======
OIOIOI
======

.. image:: https://hudson.sio2project.mimuw.edu.pl/job/oioioi-nightly-unittests/badge/icon
   :target: https://hudson.sio2project.mimuw.edu.pl/job/oioioi-nightly-unittests/Unittests_Report/

SIO2 is a free platform for carrying out algorithmic contests and OIOIOI is its
main component — the web interface.

.. contents:: :local:

Simple installation
-------------------

You can easily start development and run oioioi out of the box with `vagrant`_.
Just enter the directory where Vagrantfile and this README are placed, and type::

  vagrant up

It will create an instance of virtual machine with web server and judges running.

You can specify configuration in `vagrant.yml`. Supported configuration options (with example)::

  port: 8001  # run oioioi on port 8001 instead of the default 8000
  runserver_cmd: runserver_plus  # use manage.py runserver_plus instead of manage.py runserver

.. _vagrant: https://www.vagrantup.com/docs/

Docker Installation
-------------------

Additionally, there are available docker files to create images containing our services.

To start with, create oioioi-base image with a command::

  docker build -t oioioi-base -f Dockerfile.base .

Then run `docker-compose up` to start the infrastructure.

To start additional number of workers, use `docker-compose scale worker=<number>` as described `here`_.

To develop with docker after creating oioioi-base image, create oioioi image with::

  docker build -t oioioi .

Then run::

    OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml up

to start the infrastructure in development mode. Current dirrectory with source
code will be binded to /sio2/oioioi/ inside running container, and logs from
services will be availible outside of the container in ./logs/.

In both cases, oioioi web interface will be availible at localhost:8000, and the user
admin with password admin will be created. If you are using docker installation
in production encvironment remember to change the password.

.. _here: https://docs.docker.com/compose/reference/scale/

Manual Installation
-------------------

It should be easier to begin with a separate folder at first::

  mkdir sio2
  cd sio2

and to install OIOIOI inside a `virtualenv`_::

  virtualenv venv
  . venv/bin/activate

Then OIOIOI and its dependencies can be installed using the following commands::

  git clone git://github.com/sio2project/oioioi.git
  cd oioioi
  pip install -r requirements.txt

OIOIOI is a set of Django applications, therefore you need to create a folder with
Django settings and other deployment configuration::

  cd ..
  oioioi-create-config deployment
  cd deployment

The created *deployment* directory looks like a new Django project, but already
configured to serve the OIOIOI portal. You need to at least set the `database
configuration`_ in *settings.py*.

In case of using PostgreSQL, install Psycopg2::

  pip install psycopg2

Finally initialize the database::

  ./manage.py migrate

We use PostgreSQL.

Then you need to copy static files, like images and styles, to the deployment
directory::

  ./manage.py collectstatic

.. _virtualenv: http://www.virtualenv.org/en/latest/index.html
.. _database configuration: https://docs.djangoproject.com/en/dev/ref/settings/#databases

Basic configuration
~~~~~~~~~~~~~~~~~~~

In the simple configuration, OIOIOI will use the system-installed compilers,
and will not use the safe execution environment. User's programs will be run
with the normal user privileges. **This is not a safe configuration and the
judging will run quite slowly.** It is to easily make OIOIOI up and running for
testing purposes.

Ensure that required dependencies are installed:

* gcc/g++ (Ubuntu package: *build-essential*)
* fpc (Ubuntu package: *fp-compiler*)
* latex with support for Polish (Ubuntu packages: *texlive-latex-base*,
  *texlive-lang-polish*)
* lighttpd binary (Ubuntu package: *lighttpd*, shall not be run as service)

and in one terminal run the Django web server::

  ./manage.py runserver 0.0.0.0:8000

and in the other the evaluation daemons::

  ./manage.py supervisor

The *supervisor* process monitors all processes needed by OIOIOI, except the
web server. It has `many nice features`_.

You can create an administrator account by running::

  ./manage.py createsuperuser

If you see a locale error, you may want to circumvent it by providing
another locale to the command::

  LC_ALL=C ./manage.py createsuperuser

Now you're ready to access the site at *http://localhost:8000*.

.. _many nice features: https://github.com/rfk/django-supervisor#usage

Production configuration
~~~~~~~~~~~~~~~~~~~~~~~~

#. Begin with the simple configuration described above.

#. Make sure you are in the *deployment* folder and the virtualenv is activated.

#. Install `RabbitMQ`_. We tested version 2.8.6 from `RabbitMQ Debian/Ubuntu
   Repos`_. Anything newer should work as well.

#. Uncomment and set *BROKER_URL* in *settings.py* to point to the configured
   RabbitMQ vhost. The default setting corresponds to the default RabbitMQ
   installation.

#. Download sandboxes::

     ./manage.py download_sandboxes

#. Disable system compilers and unsafe code execution by commenting out
   *USE_UNSAFE_EXEC = True* and *USE_LOCAL_COMPILERS = True* in *settings.py*.

#. (optionally) Disable starting the judging process on the server, especially
   if you want to configure judging machines (see below) for judging, what is
   strongly recommended. Comment out the *RUN_LOCAL_WORKERS = True* setting.

#. (required only for dedicated judging machines) Configure Filetracker server by
   setting *FILETRACKER_LISTEN_ADDR* and *FILETRACKER_URL* in *settings.py* and
   restart the daemons.

#. Ensure that production-grade dependencies are installed:

   * uwsgi (*pip install uwsgi*)

#. Install and configure web server. We recommend using nginx with uwsgi plugin
   (included in *nginx-full* Ubuntu package). An example configuration is
   automatically created as *nginx-site.conf*. Have a look there. What you
   probably want to do is (as root)::

     cp nginx-site.conf /etc/nginx/sites-available/oioioi
     ln -s ../sites-available/oioioi /etc/nginx/sites-enabled/
     service nginx reload

   Once this is done, you no more need to run *manage.py runserver*.

   If you prefer deploying with Apache, an example configuration is created
   as *apache-site.conf*. You would need to install *apache2* and
   *libapache2-mod-uwsgi* packages.

#. Comment out *DEBUG = True* in *settings.py*. This is crucial for security
   and efficiency. Also `set ALLOWED_HOSTS`_.

#. Set admin email in settings. Error reports and teacher account requests will
   be sent there.

#. Set SMTP server in settings. Otherwise new user registration (among others)
   will not work.

#. You probably want to run *manage.py supervisor -d* automatically when the
   system starts. One way is to add the following line to the OIOIOI user's
   crontab (``crontab -e``)::

     @reboot <deployment_folder>/start_supervisor.sh

#. (optionally) If you have efficiency problems or expect heavy load, you may
   consider using gevent as uwsgi event loop. To do so, `install gevent`_ and
   set UWSGI_USE_GEVENT flag in *settings.py*.

#. (optionally) You can also enable content caching. To do so, first you have
   to install dependencies:

   * memcached (Ubuntu package: *memcached*)
   * python-memcached (*pip install python-memcached*)

   Next, you have to uncomment the corresponding lines under "Cache" in
   *settings.py* and set the address of your memcached instance. Note that you
   can run memcached locally or on a remote server. For more information about
   memcached configuration see `official documentation`_.

#. (optionally) You can ensure users are automatically notified of certain
   events in the system - or notify them on your own - just enable
   the Notifications Server.
   For more information, consult the *notifications/README.rst* file.

.. _judging-machines:
.. _install gevent: https://github.com/surfly/gevent#installing-from-github
.. _set ALLOWED_HOSTS: https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
.. _official documentation: https://code.google.com/p/memcached/wiki/NewStart

Setting up judging machines
~~~~~~~~~~~~~~~~~~~~~~~~~~~

On every judging machine do the following:

#. Create a new user account for the judging processes and switch to it.

#. Set up virtualenv::

     virtualenv venv
     . venv/bin/activate

#. Download and install the *sioworkers* package::

     git clone https://github.com/sio2project/sioworkers
     cd sioworkers
     python setup.py install

#. Copy and adjust configuration files::

     cp config/supervisord.conf{.example,}
     cp config/supervisord-conf-vars.conf{.example,}

   Modify SIOWORKERSD_HOST and FILETRACKER_URL variables in
   *config/supervisord-conf-vars.conf*. By default, sioworkersd is run
   by supervisor on the same host as OIOIOI (SIO2). Filetracker server is also
   run there, by default on port 9999. You should consider changing
   WORKER_CONCURRENCY to smaller value if you are judging problems without
   oitimetool (depends on rules of concrete contest and USE_UNSAFE_EXEC
   in *deployment/settings.py* on OIOIOI host).

#. Start the supervisor::

     ./supervisor.sh start

#. You probably want to have the worker started automatically when system
   starts. In order to have so, add the following line to the sioworker user's
   crontab (``crontab -e``)::

     @reboot <deployment_folder>/supervisor.sh start

Final notes
~~~~~~~~~~~

It is strongly recommended to install the *librabbitmq* Python module (on the
server). We observed some not dispatched evaluation requests when running
celery with its default AMQP binding library::

  pip install librabbitmq

Celery will pick up the new library automatically, once you restart the
daemons using::

  ./manage.py supervisor restart all

.. _RabbitMQ: http://www.rabbitmq.com/
.. _RabbitMQ Debian/Ubuntu Repos: http://www.rabbitmq.com/install-debian.html

Installing on 64-bit machines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sandboxes provided by the SIO2 Project contain 32-bit binaries. Therefore
it is recommended that OIOIOI is installed on a 32-bit Linux system. Otherwise,
required libraries may be missing. Here we list some of them, which we found
needed when installing OIOIOI in a pristine Ubuntu Server 12.04 LTS (Precise
Pangolin):

* *libz* (Ubuntu package: *zlib1g:i386*)

Upgrading
---------

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

Usage
-----

Well, we don't have a full-fledged User's Guide, but feel free to propose
what should be added here.

Creating task packages
~~~~~~~~~~~~~~~~~~~~~~

To run a contest, you obviously need some tasks. To add a task to a contest in
OIOIOI, you need to create an archive, called task package. Here are some
pointers, how it should look like:

* `example task packages`_ used by our tests,
* `a rudimentary task package format specification`_.

.. _example task packages: https://github.com/sio2project/oioioi/tree/master/oioioi/sinolpack/files
.. _a rudimentary task package format specification: http://sio2project.mimuw.edu.pl/display/DOC/Preparing+Task+Packages

Testing
-----

OIOIOI has a big suite of unit tests. All utilites that are useful for testing
can be found in ``test/`` directory. Currently these are:

* ``test.sh`` - a simple test runner
* ``test_parallel.py`` - runs the same tests as test.sh, but uses multiple processes
* ``loadtest.py`` - load testing script

Backup
-----

Amanda is recommended for doing OIOIOI backups. Sample configuration with README
is available in ``extra/amanda`` directory.

Contact us
------------

Additional information can be found on our:

* `official website`_
* `project documentation`_
* `issue tracker`_

If you have any further questions regarding installation, configuration or
usage of OIOIOI, there are some places you can reach us through:

* `our mailing list`_
* `GitHub issues system`_ (English only)

.. _official website: http://sio2project.mimuw.edu.pl
.. _project documentation: http://oioioi.readthedocs.org/en/latest/
.. _issue tracker: http://jira.sio2project.mimuw.edu.pl

.. _our mailing list: sio2-project@googlegroups.com
.. _GitHub issues system: http://github.com/sio2project/oioioi/issues
