======
OIOIOI
======

SIO2 is a free platform for carrying out algorithmic contests and OIOIOI is its
main component — the web interface.

Installation
------------

Docker (for deployment)
~~~~~~~~~~~~~~~~~~~~~~~

You can manually use docker files to create images containing our services.

To run the infrastructure simply::

  "OIOIOI_VERSION=<oioioi_version>" docker compose up

Make sure to change default superuser password, same as in the automatic method.

To start additional number of workers::

  "OIOIOI_VERSION=<oioioi_version>" docker compose up --scale worker=<number>

as described `in Docker docs`_.

.. _in Docker docs: https://docs.docker.com/compose/reference/up/

Docker image
============
.. _official Docker image: https://github.com/sio2project/oioioi/pkgs/container/oioioi

An `official Docker image`_ for oioioi is available on the GitHub Container Registry.

Docker (for development)
~~~~~~~~~~~~~~~~~~~~~~~

Make sure you installed docker properly. The easiest way to do this::

    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh

Start docker service::

    sudo systemctl start docker

Then add yourself to group docker -- to create a group use::

    sudo groupadd docker
    gpasswd -a $USER docker
    newgrp docker

It is possible that you will need to log out and log in. Type docker ps into your terminal to check if everything was installed properly.
If you skip the step above, you will either have to use sudo every time you use docker or use docker above 19.03 version with
experimental features enabled.

Prepare the image with::

    OIOIOI_UID=$(id -u) docker compose -f docker-compose-dev.yml build

Then you can start oioioi with::

    OIOIOI_UID=$(id -u) docker compose -f docker-compose-dev.yml up -d
    OIOIOI_UID=$(id -u) docker compose -f docker-compose-dev.yml exec web python3 manage.py runserver 0.0.0.0:8000

to start the infrastructure in the development mode. Current directory with the source code will be bound to /sio2/oioioi/ inside the running container.

oioioi web interface will be available at localhost:8000, and the user admin with password admin will be created.

Additionally you can bind config files and logs folder to the host::

    id=$(docker create sio2project/oioioi-dev)  #Create oioioi container
    docker cp $id:/sio2/deployment deployment  #Copy initial deployment folder from oioioi container
    docker rm -v $id  #Remove unneeded container

Remember to also uncomment the appropriate volume binding in the web service description in the docker-compose-dev.yml.

Running tests on Docker
~~~~~~~~~~~~~~~~~~~~~~~

For testing purposes we use test.sh script located in oioioi directory. Note it's not the same directory
you are connected to after using docker exec -it “web” /bin/bash. The default container id that you should use for running tests is "web"::

    docker compose -f docker-compose-dev.yml exec "web" ../oioioi/test.sh
    docker compose -f docker-compose-dev.yml exec "web" ../oioioi/test.sh oioioi/{name_of_the_app}/

Running static code analysis tools locally (requires Docker)
~~~~~~~~~~~~~~~~~~~~~~~

The static code analysis tools currently in use for python code are black, isort, pep8 and pylint.
All of them can be run locally using the `run_static.sh` shell script.
In order for the script to work the `web` container from docker-compose-dev.yml needs to be running.
The docker image for the project needs to be rebuild if you are migrating from and older Dockerfile version (rebuild the image if you are getting error messages that isort or black are not installed).
Commands for building the image and starting up the containers are listed in the paragraphs above.

When running all tools at once or when running pep8 and pylint independently only the recently modified files (files modified in the most recent commit or staged changes) will be processed.

To run all tools at once::

    ./run_static.sh

To run one of the tools::

    ./run_static.sh black
    ./run_static.sh isort
    ./run_static.sh pylint
    ./run_static.sh pep8

Script toolbox for Docker (development)
~~~~~~~~~~~~~~~~~~~~~~~~~
Copy-pasting all Docker commands from GitHub can be tedious. Instead use a set of pre-prepared commands embedded into `easy_toolbox.py`.
For help run `easy_toolbox.py -h`. Add custom commands by editing `RAW_COMMANDS` in the file. Script can be used with user-friendly
CLI or by passing commands as arguments.
Developer environment can be easily set up by running::

    ./easy_toolbox.py build
    ./easy_toolbox.py up
    # wait for the scripts to finish migration (up to one minute)
    ./easy_toolbox.py run

For system requirements check `easy_toolbox.py`.

Manual installation (deprecated)
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
* ``tox [path/to/module[::TestClass[::test_method]]] [-- arg1 arg2 ...]`` - runs pytest in isolated environment

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
