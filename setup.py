# -*- coding: utf-8 -*-

from __future__ import print_function
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os
import sys

if os.getuid() == 0:  # root
    print("ERROR: This setup.py cannot be run as root.", file=sys.stderr)
    print("ERROR: If you want to proceed anyway, hunt this", file=sys.stderr)
    print("ERROR: message and edit the source at your own risk.", file=sys.stderr)
    sys.exit(2)

PYTHON_VERSION = sys.version_info[0]

python2_specific_requirements = [
    "pdfminer>=20110515,<20131113",
    "slate",
    "django-supervisor",
    "supervisor",
]

python3_specific_requirements = [
    "pdfminer3k",
    "slate3k",
]

python23_universal_requirements = [
        "Django>=1.9,<1.10",  # when upgrading, upgrade also django-two-factor-auth!
        "pytz>=2013b",
        "django-otp==0.3.4",  # latest version for Django 1.9 and django-two-factor-auth 1.5.0
        "sqlalchemy",
        "beautifulsoup4",
        "PyYAML",
        "python-dateutil",
        "django-two-factor-auth==1.5.0",  # latest version for Django 1.9

        "django-registration-redux>=1.6,<2.0",

        "Celery>=3.1.15,<4.0.0",
        "django-celery>=3.1.15,<=3.1.17",
        "dj-pagination",
        "django-compressor==2.2",
        "django-overextends>=0.4.1",
        "pygments",
        "django-libsass>=0.7",

        "django-debug-toolbar>=1.4",
        "django-extensions>=1.0.0",
        "werkzeug",

        'pytest',
        'pytest-django',
        'pytest-html',
        'pytest-xdist',
        'pytest-cov',

        # http://stackoverflow.com/questions/31417964/importerror-cannot-import-name-wraps
        # ¯\_(ツ)_/¯
        "mock==1.0.1",

        "fpdf",
        "unicodecsv",
        "shortuuid",
        "enum34",
        "dnslib",
        "bleach==1.5",

        "chardet",

        "django-gravatar2",

        "django-mptt>=0.8.7,<0.9.1",

        "mistune",

        # Some of celery dependencies (kombu) require amqp to be <2.0.0
        "amqp<2.0.0",

        "pika",

        "raven",
        "unidecode",

        # A library allowing to nest inlines in django admin.
        # Used in quizzes module for adding new quizzes.
        "django-nested-admin",

        # SIO2 dependencies:
        "filetracker>=2.1,<3.0",

        # Dependencies from external sources live in requirements.txt
]

if PYTHON_VERSION == 2:
    final_requirements = python23_universal_requirements + python2_specific_requirements
else:
    final_requirements = python23_universal_requirements + python3_specific_requirements

setup(
    name='oioioi',
    version='0.1.1.dev',
    description='The web frontend of the SIO2 Project contesting system',
    author='The SIO2 Team',
    author_email='sio2@sio2project.mimuw.edu.pl',
    url='http://sio2project.mimuw.edu.pl',
    install_requires=final_requirements,

    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='oioioi.runtests.runtests',

    entry_points={
        'console_scripts': [
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
