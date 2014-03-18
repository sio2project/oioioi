======
OIOIOI
======

.. image:: https://hudson.sio2project.mimuw.edu.pl/job/oioioi-github-unittests/badge/icon
   :target: https://hudson.sio2project.mimuw.edu.pl/job/oioioi-github-unittests/Unittests_Report/

SIO2 is a free platform for carrying out algorithmic contests and OIOIOI is its
main component --- the web interface.

Installation
------------

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

OIOIOI is a set of Django Applications, so you need to create a folder with
Django settings and other deployment configuration::

  oioioi-create-config deployment
  cd deployment

The created *deployment* directory looks like a new Django project, but already
configured to serve the OIOIOI portal. You need to at least set the `database
configuration`_ in *settings.py*.

In case of using PostgreSQL, install Psycopg2::

  pip install psycopg2

Finally initialize the database::

  ./manage.py syncdb
  ./manage.py migrate

We use PostgreSQL.

.. _virtualenv: http://www.virtualenv.org/en/latest/index.html
.. _database configuration: https://docs.djangoproject.com/en/dev/ref/settings/#databases

Simple configuration
~~~~~~~~~~~~~~~~~~~~

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
* lessc (`LESS`_ compiler, **minimum version 1.3.3**; on Ubuntu install *npm*
  and then run ``sudo npm install --global less``; can also `be installed inside
  virtualenv`_)

and in one terminal run the Django web server::

  ./manage.py runserver 0.0.0.0:8000

and in the other the evaluation daemons::

  ./manage.py supervisor

The *supervisor* process monitors all processes needed by OIOIOI, except the
web server. It has `many nice features`_.

Finally, if you didn't create an administrator account when running *syncdb*,
you can do it now::

  ./manage.py createsuperuser

If you see a locale error, you may want to circumvent it by providing
another locale to the command::

  LC_ALL=C ./manage.py createsuperuser

Now you're ready to access the site at *http://localhost:8000*.

.. _LESS: http://lesscss.org/
.. _many nice features: https://github.com/rfk/django-supervisor#usage
.. _be installed inside virtualenv: http://pastebin.com/u8nSj0yS

Production configuration
~~~~~~~~~~~~~~~~~~~~~~~~

#. Begin with the simple configuration described above.

#. Ensure that production-grade dependencies are installed:

   * lighttpd binary (Ubuntu package: *lighttpd*, shall not be run as service.)
   * uwsgi (*pip install uwsgi*)

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

#. (optionally) Enable Filetracker server by uncommenting corresponding lines
   in *settings.py* and restart the daemons. This is required for dedicated
   judging machines.

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

.. _judging-machines:
.. _install gevent: https://github.com/surfly/gevent#installing-from-github
.. _set ALLOWED_HOSTS: https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts

Setting up judging machines
~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Create a new user account for the judging processes and switch to it.

#. Set up virtualenv::

     virtualenv venv
     . venv/bin/activate

#. Install the *sioworkers* package::

     pip install sioworkers

#. Start the worker process::

     sio-celery-worker BROKER_URL

   The passed argument must point to the RabbitMQ server configured on the
   server machine.

#. That's all. You probably want to have the worker started automatically when
   system starts. We do not have a ready-made solution for this yet. Sorry!

The worker assumes that the Filetracker server is running on the same server as
RabbitMQ, on the default port 9999. If this is not the case, you should pass
the Filetracker server URL in the *FILETRACKER_URL* environment variable.

Final notes
~~~~~~~~~~~

It is strongly recommended to install the *librabbitmq* Python module (on the
server *and the worker machines*). We observed some not dispatched evaluation
requests when running celery with its default AMQP binding library::

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
  ./manage.py syncdb
  ./manage.py migrate
  ./manage.py collectstatic
  ./manage.py supervisor restart all

and restart the judging machines.

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

Contact us
------------

Should you have any further questions regarding installation, configuration or
usage of OIOIOI, feel free to contact us by an `e-mail`_,
via IRC (#tagtag at freenode) or through `github issues system`_. Please use
English on github and English or Polish elsewhere. You may find some additional
information on our `official website`_ and in the official `project documentation`_.
You can also look at what we are currently working on by browsing current tickets on
our `issue tracker`_.

.. _e-mail: sio2-project@googlegroups.com
.. _github issues system: http://github.com/sio2project/oioioi/issues
.. _official website: http://sio2project.mimuw.edu.pl
.. _project documentation: http://oioioi.readthedocs.org/en/latest/
.. _issue tracker: http://jira.sio2project.mimuw.edu.pl
