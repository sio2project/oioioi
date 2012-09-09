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

Then OIOIOI and its dependencies can be installed by simply running::

  pip install -e git://github.com/sio2project/oioioi.git#egg=oioioi

This will also store the source code in *venv/src*. There is no official release
yet, so a simple ``pip install oioioi`` wouldn't work.

OIOIOI is a set of Django Applications, so you need to create a folder with
Django settings and other deployment configuration::

  oioioi-create-config deployment
  cd deployment

The created *deployment* directory looks like a new Django project, but already
configured to serve the OIOIOI portal. You need to at least set the `database
configuration`_ in *settings.py* and initialize it::

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
* latex with support for Polish (Ubuntu packages: *texlive-latex*,
  *texlive-lang-polish*)
* lessc (`LESS`_ compiler, **minimum version 1.3.0**; on Ubuntu install *npm*
  and then run ``sudo npm install --global less``)

and in one terminal run the Django web server::

  ./manage.py runserver 0.0.0.0:8000

and in the other the evaluation daemons::

  ./manage.py supervisor

The *supervisor* process monitors all processes needed by OIOIOI, except the
web server. It has `many nice features`_.

Finally, if you didn't create an administrator account when running *syncdb*,
you can do it now::

  ./manage.py createsuperuser

Now you're ready to access the site at *http://localhost:8000*.

.. _LESS: http://lesscss.org/
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

#. (optionally) Enable Filetracker server by uncommenting corresponding lines
   in *settings.py* and restart the daemons.

#. Configure Apache with mod_wsgi. An example configuration is automatically
   created as *apache-site.conf*. Have a look there. Once this is done, you
   do not need to run *manage.py runserver*.

#. Comment out *DEBUG = True* in *settings.py*. This is crucial for security
   and efficiency.

#. Set admin email in settings. Error reports and teacher account requests will
   be sent there.

#. You probably want to run *manage.py supervisor* automatically when the
   system starts. We do not have a ready-made solution for this yet. Sorry!

.. _judging-machines:

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
daemons.

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

Installing on Ubuntu
~~~~~~~~~~~~~~~~~~~~

Ubuntu has one `additional security feature`_ which interferes with the
instruction counting sandbox used by default by OIOIOI. It must be disabled
by adding the following line to */etc/sysctl.conf*::

  kernel.yama.ptrace_scope = 0

and rebooting the machine or reloading this file with ``sudo sysctl -p``.

.. _additional security feature: https://wiki.ubuntu.com/Security/Features#ptrace_scope
