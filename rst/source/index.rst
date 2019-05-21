.. OIOIOI Documentation Index File

OIOIOI Developer's Reference
============================

This is the reference documentation for the OIOIOI Project.

There is also some documentation on the `OIOIOI Project Documentation Site
<http://sio2project.mimuw.edu.pl/display/DOC>`_.

Architecture Overview
---------------------

.. _Django 1.10: https://docs.djangoproject.com/en/1.10/
.. _Django authentication: https://docs.djangoproject.com/en/1.10/topics/auth/
.. _django-registration-redux: http://django-registration-redux.readthedocs.org/en/latest/
.. _Django file storage: https://docs.djangoproject.com/en/1.10/topics/files/
.. _Filetracker: https://github.com/sio2project/filetracker
.. _Sioworkers: https://github.com/sio2project/sioworkers
.. _Celery: http://docs.celeryproject.org/en/latest/index.html
.. _djcelery: http://docs.celeryproject.org/en/latest/django/index.html
.. _django-pagination: https://code.google.com/p/django-pagination/
.. _django-nose: https://github.com/jbalogh/django-nose
.. _selenium: http://www.seleniumhq.org/
.. _Django i18n: https://docs.djangoproject.com/en/1.10/topics/i18n/
.. _Transifex: https://www.transifex.com/projects/p/sio2project/

The OIOIOI source code is a standard `Django 1.10`_ project, with the following
components used:

* Standard `Django authentication`_
* User registration with `django-registration-redux`_
* :doc:`Modified Django file storage </sections/filestorage>`

  * custom storage class :class:`~oioioi.filetracker.storage.FileTrackerStorage`
  * custom :func:`~oioioi.filetracker.utils.filename_generator` to pass as ``FileField.upload_to``
  * `Filetracker`_

* Distributed judging

  * an :doc:`evaluation manager </sections/evaluation>` running on
    `Celery`_ (Django bindings with `djcelery`_)
  * evaluation code running on judging machines is external to OIOIOI (see
    `Sioworkers`_)

* Pagination with `django-pagination`_
* Testing with `django-nose`_ and `selenium`_
* Standard `Django i18n`_ with translations managed by `Transifex`_


Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    sections/modules
    sections/filestorage
    sections/scoring
    sections/evaluation
    sections/problem_uploading
    sections/controllers
    sections/notifications
    sections/mixins
    sections/misc
    glossary

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
