# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os
import sys

if not sys.version_info[0] == 2:
    print >>sys.stderr, "ERROR: Wrong python version."
    print >>sys.stderr, "ERROR: You can only run this using Python 2."
    sys.exit(2)


if os.getuid() == 0:  # root
    print >>sys.stderr, "ERROR: This setup.py cannot be run as root."
    print >>sys.stderr, "ERROR: If you want to proceed anyway, hunt this"
    print >>sys.stderr, "ERROR: message and edit the source at your own risk."
    sys.exit(2)

setup(
    name='oioioi',
    version='0.1.1.dev',
    description='The web frontend of the SIO2 Project contesting system',
    author='The SIO2 Team',
    author_email='sio2@sio2project.mimuw.edu.pl',
    url='http://sio2project.mimuw.edu.pl',
    install_requires=[
        "Django>=1.9,<1.10",  # when upgrading, upgrade also django-two-factor-auth!
        "pytz>=2013b",
        "sqlalchemy",
        "bs4",
        "PyYAML",
        "python-dateutil",
        # Earlier versions of django-nose are incompatible with Django 1.9
        "django-nose>=1.4",
        "nose-picker>=0.5.3",
        "django-two-factor-auth==1.5.0",  # latest version for Django 1.9

        "django-registration-redux>=1.6,<2.0",

        "Celery>=3.1.15,<4.0.0",
        "django-celery>=3.1.15,<=3.1.17",
        "django-supervisor",
        "dj-pagination",
        "django-compressor==2.2",
        "django-overextends>=0.4.1",
        "pygments",
        "django-libsass>=0.7",

        "django-debug-toolbar>=1.4",
        "django-extensions>=1.0.0",
        "werkzeug",

        "nose >= 1.3",

        "nose-capturestderr",
        "nose-html",
        "nose-profile",
        "nose-exclude",

        # http://stackoverflow.com/questions/31417964/importerror-cannot-import-name-wraps
        # ¯\_(ツ)_/¯
        "mock==1.0.1",

        "fpdf",
        "pdfminer>=20110515,<20131113",
        "slate",
        "unicodecsv",
        "shortuuid",
        "enum34",
        "dnslib",
        "bleach==1.5",

        "chardet",

        "django-gravatar2",

        "django-mptt>=0.8.7",

        "mistune",

        # Some of celery dependencies (kombu) require amqp to be <2.0.0
        "amqp<2.0.0",

        # A library required by AMQP, used in notifications system.
        # We need version >= 1.5.1, becuase it has fixed this bug
        # https://github.com/celery/librabbitmq/issues/42
        "librabbitmq>=1.5.1",

        "raven",
        "unidecode",

        # A library allowing to nest inlines in django admin.
        # Used in quizzes module for adding new quizzes.
        "django-nested-admin"

        # Dependencies from external sources live in requirements.txt
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='oioioi.runtests.runtests',

    entry_points={
        'console_scripts': [
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
