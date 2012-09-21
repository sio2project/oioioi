.. OIOIOI Documentation Index File

OIOIOI Developer's Reference
============================

This is the reference documentation for the OIOIOI Project.

There is way more documentation on the `OIOIOI Project Documentation Site
<http://sio2project.mimuw.edu.pl/display/DOC>`_.

Architecture Overview
---------------------

.. _Django 1.4: https://docs.djangoproject.com/en/1.4/
.. _Django authentication: https://docs.djangoproject.com/en/1.4/topics/auth/
.. _django-registration: https://bitbucket.org/ubernostrum/django-registration/
.. _South: http://south.readthedocs.org/en/latest/
.. _Django file storage: https://docs.djangoproject.com/en/1.4/topics/files/
.. _Filetracker: ../../../../lib/filetracker/rst/build/html/index.html
.. _Celery: http://docs.celeryproject.org/en/latest/index.html
.. _djcelery: http://docs.celeryproject.org/en/latest/django/index.html
.. _Celery periodic scheduler: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html
.. _django-pagination: https://code.google.com/p/django-pagination/
.. _django-nose: https://github.com/jbalogh/django-nose
.. _Django i18n: https://docs.djangoproject.com/en/1.4/topics/i18n/

The OIOIOI source code is a standard `Django 1.4`_ project, with the following
components used:

* Standard `Django authentication`_
* User registration with `django-registration`_
* Database migrations with `South`_
* :doc:`Modified Django file storage </sections/filestorage>`

  * custom storage class :class:`~oioioi.filetracker.storage.FileTrackerStorage`
  * custom :func:`~oioioi.filetracker.utils.filename_generator` to pass as ``FileField.upload_to``
  * `Filetracker`_

* Distributed judging with `Celery`_

  * Django bindings with `djcelery`_
  * evaluation code running on judging machines is external to OIOIOI (see
    :ref:`workers`)
  * but we also have an :doc:`evaluation manager </sections/evaluation>` running on
    Celery
  * and we use `Celery periodic scheduler`_ for running maintenance tasks

* Pagination with `django-pagination`_
* Testing with `django-nose`_
* Standard `Django i18n`_


Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    sections/filestorage
    sections/scoring
    sections/evaluation
    sections/misc
    glossary

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
