======
OIOIOI
======

SIO2 is a free platform for carrying out algorithmic contests and OIOIOI is its
main component — the web interface.

Installation
------------

Easy Installer
~~~~~~~~~~~~~~~~~~~~~~~~~

You can easily install and run oioioi out of the box with oioioi_easy_installer.
Just download the oioioi_easy_installer archive, unpack it and run::

  ./oioioi.sh install

to install oioioi. Then you can run::

  ./oioioi.sh start
  ./oioioi.sh stop

to start and stop oioioi.

Make sure to change default superuser password. To do that:
   1. Login to the superuser with default credentials (username:admin, password:admin).
   2. Click username ("admin") in upper-right corner of the webpage.
   3. Click "Change password".
   4. Fill and submit password change form.

You can also update your oioioi instance by typing::

  ./oioioi.sh update

Docker (for deployment)
~~~~~~~~~~~~~~~~~~~~~~~

The easy installer method above uses Docker under the hood. Additionally, you can manually use docker files to create images containing our services.

To run the infrastructure simply::

  "OIOIOI_CONFIGDIR=<config directory>" "OIOIOI_VERSION=<oioioi_version>" docker-compose up

Make sure to change default superuser password, same as in the automatic method.

To start additional number of workers::

  "OIOIOI_CONFIGDIR=<config directory>" "OIOIOI_VERSION=<oioioi_version>" docker-compose up --scale worker=<number>

as described `in Docker docs`_.

.. _in Docker docs: https://docs.docker.com/compose/reference/up/

Docker (for development)
~~~~~~~~~~~~~~~~~~~~~~~

First prepare the image with::

    OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml build

Then you can start oioioi with::

    OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml up
    OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python manage.py runserver

to start the infrastructure in the development mode. Current dirrectory with the source code will be bound to /sio2/oioioi/ inside the running container.

oioioi web interface will be available at localhost:8000, and the user admin with password admin will be created.

Additionally you can bind config files and logs folder to the host::

    id=$(docker create oioioi-dev)  #Create oioioi container
    docker cp $id:/sio2/deployment deployment  #Copy initial deployment folder from oioioi contanier
    docker rm -v $id  #Remove unneeded container

Remember to also uncomment the appropriate volume binding in the web service description in the docker-compose-dev.yml.

Manual installation
~~~~~~~~~~~~~~~~~~~

See `INSTALL`_ for instructions.

.. _INSTALL: INSTALL.rst

Upgrading
---------

See `UPGRADING`_ for instructions.

.. _UPGRADING: UPGRADING.rst

Backup
------

Amanda is recommended for doing OIOIOI backups. Sample configuration with README
is available in ``extra/amanda`` directory.

For developers
--------------

Documentation for developers:

* `Developer's Guide`_
* `Developer's Reference`_

.. _Developer's Guide: CONTRIBUTING.rst
.. _Developer's Reference: http://oioioi.readthedocs.io/en/latest/

Testing
-------

OIOIOI has a big suite of unit tests. You can run them in following way:

* ``test.sh`` - a simple test runner, use from virtualenv
* ``test_selenium.sh`` - long selenium tests, use from virtualenv
* ``tox [path/to/module[::TestClass[::test_method]]] [-- arg1 arg2 ...]`` - runs pytest in isolated environemnt

Supported args:

* ``-n NUM`` - run tests using NUM CPUs
* ``-v`` - increase verbosity
* ``-q`` - decrease verbosity
* ``-x`` - exit after first failure
* ``-lf`` - runs only tests that failed last time
* ``--runslow`` - runs also tests marked as slow

Usage
-----

Well, we don't have a full-fledged User's Guide, but feel free to propose
what should be added here.

Creating task packages
~~~~~~~~~~~~~~~~~~~~~~

To run a contest, you obviously need some tasks. To add a task to a contest in
OIOIOI, you need to create an archive, called task package. Here are some
pointers, how it should look like:

* `tutorial`_,
* `example task packages`_ used by our tests,
* `a rudimentary task package format specification`_.

.. _tutorial: https://github.com/sio2project/oioioi/wiki
.. _example task packages: https://github.com/sio2project/oioioi/tree/master/oioioi/sinolpack/files
.. _a rudimentary task package format specification: http://sio2project.mimuw.edu.pl/display/DOC/Preparing+Task+Packages

Contact us
------------

Here are some useful links:

* `our mailing list`_
* `GitHub issues system`_ (English only)

.. _our mailing list: sio2-project@googlegroups.com
.. _GitHub issues system: http://github.com/sio2project/oioioi/issues
