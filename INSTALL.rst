=================
Installing OIOIOI
=================

First, ensure that all dependencies are installed:

* gcc/g++ (Ubuntu package: *build-essential*)
* fpc (Ubuntu package: *fp-compiler*)
* latex with languages used in sample tasks (Ubuntu packages:
  *texlive-latex-base*, *texlive-lang-polish*,
  *texlive-lang-czechslovak*, *texlive-lang-european*,
  *texlive-lang-german*)
* latex packages (*texlive-latex-extra*, *texlive-fonts-recommended*, *tex-gyre*,
  *texlive-pstricks*, *lmodern*),
* Berkeley DB library (Ubuntu package: *libdb-dev*)
* Node.js and npm (Ubuntu packages: *nodejs*, *npm*),

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
  npm install
  npm run build
  
OIOIOI is a set of Django applications, therefore you need to create a folder with
Django settings and other deployment configuration::

  cd ..
  oioioi-create-config deployment
  cd deployment

The created *deployment* directory looks like a new Django project, but already
configured to serve the OIOIOI portal. You need to at least set the `database
configuration`_ in *settings.py*.

In case of using PostgreSQL, install Psycopg2::

  pip install psycopg2-binary

Finally initialize the database::

  ./manage.py migrate

We use PostgreSQL.

Then you need to copy static files, like images and styles, to the deployment
directory::

  ./manage.py collectstatic

.. _virtualenv: http://www.virtualenv.org/en/latest/index.html
.. _database configuration: https://docs.djangoproject.com/en/dev/ref/settings/#databases

Basic configuration
-------------------

In the simple configuration, OIOIOI will use the system-installed compilers,
and will not use the safe execution environment. User's programs will be run
with the normal user privileges. **This is not a safe configuration and the
judging will run quite slowly.** It is to easily make OIOIOI up and running for
testing purposes.

Run the Django web server and the evaluation daemons::

  ./manage.py supervisor

The *supervisor* process monitors all processes needed by OIOIOI, including the
web server. It has `many nice features`_.

You can create an administrator account by running::

  ./manage.py createsuperuser

If you see a locale error, you may want to circumvent it by providing
another locale to the command::

  LC_ALL=C ./manage.py createsuperuser

Now you're ready to access the site at *http://localhost:8000*.

.. _many nice features: https://github.com/rfk/django-supervisor#usage

Production configuration
------------------------

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
   *USE_UNSAFE_EXEC = True* and *AVAILABLE_COMPILERS = SYSTEM_COMPILERS* and
   *DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS* in *settings.py*.

#. (optionally) Disable starting the judging process on the server, especially
   if you want to configure judging machines (see below) for judging, what is
   strongly recommended. Comment out the *RUN_LOCAL_WORKERS = True* setting.

#. (required only for dedicated judging machines) Configure Filetracker server by
   setting *FILETRACKER_LISTEN_ADDR* and *FILETRACKER_URL* in *settings.py* and
   restart the daemons.

#. Ensure that production-grade dependencies are installed:

   * uwsgi (*pip install uwsgi*)

#. Turn on UWSGI by setting *SERVER* to *uwsgi* in *settings.py* and restart
   the supervisor.

#. Install and configure web server. We recommend using nginx with uwsgi plugin
   (included in *nginx-full* Ubuntu package). An example configuration is
   automatically created as *nginx-site.conf*. Have a look there. What you
   probably want to do is (as root)::

     cp nginx-site.conf /etc/nginx/sites-available/oioioi
     ln -s ../sites-available/oioioi /etc/nginx/sites-enabled/
     service nginx reload

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
---------------------------

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
   sio2jail, so that each process has enough memory (depends on rules of concrete
   contest and USE_UNSAFE_EXEC in *deployment/settings.py* on OIOIOI host).

#. Start the supervisor::

     ./supervisor.sh start

#. You probably want to have the worker started automatically when system
   starts. In order to have so, add the following line to the sioworker user's
   crontab (``crontab -e``)::

     @reboot <deployment_folder>/supervisor.sh start

Final notes
-----------

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
-----------------------------

The sandboxes provided by the SIO2 Project contain 32-bit binaries. Therefore
it is recommended that OIOIOI is installed on a 32-bit Linux system. Otherwise,
required libraries may be missing. Here we list some of them, which we found
needed when installing OIOIOI in a pristine Ubuntu Server 12.04 LTS (Precise
Pangolin):

* *libz* (Ubuntu package: *zlib1g:i386*)

