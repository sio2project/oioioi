# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    from setuptools import find_packages, setup
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
    "django-supervisor",
    "supervisor",
]

python3_specific_requirements = []

python23_universal_requirements = [
    "Django>=1.11,<1.12",  # when upgrading, upgrade also django-two-factor-auth!
    "pytz>=2013b",
    "sqlalchemy",
    # latest version of django-otp for Django 1.10 and django-two-factor-auth 1.6.*
    "django-otp>=0.4.3,<0.5",
    "beautifulsoup4",
    "PyYAML",
    "python-dateutil",
    "django-two-factor-auth<1.7",  # latest version for Django 1.10
    "django-formtools<2.2",  # latest version for Django 1.10 and
    # django-two-factor-auth 1.6.*; can be
    # removed after migration to Django 1.11
    "django-registration-redux>=1.6,<2.0",  # latest for Django 1.10
    "Celery>=3.1.15,<4.0.0",
    "coreapi>=2.3.0",
    "dj-pagination>=2.3.3.final.0",
    "django-compressor==2.2",  # latest version
    "django-overextends>=0.4.1",
    "pygments",
    "django-libsass>=0.7",
    "django-debug-toolbar>=1.9.1,<1.10",  # latest version for Django 1.10
    "django-extensions>=2.2.9,<3.0",  # latest version for Django 1.11
    "djangorestframework==3.8.2",  # latest version for Django 1.10
    "werkzeug",
    'pytest==4.6.11',
    'pytest-django==3.10.0',
    'pytest-html==1.22.1',
    'pytest-xdist==1.34.0',
    'pytest-cov>=2.11,<2.12',
    'requests<3',
    # http://stackoverflow.com/questions/31417964/importerror-cannot-import-name-wraps
    # ¯\_(ツ)_/¯
    "mock==1.0.1",
    "fpdf",
    "unicodecsv",
    "shortuuid",
    "enum34",
    "dnslib",
    "bleach>=3.1.0,<3.2",
    "chardet",
    "django-gravatar2",
    "django-mptt>=0.8.7,<0.9.1",  # latest version for Dango 1.11, supports 2.0
    "mistune",
    # Some of celery dependencies (kombu) require amqp to be <2.0.0
    "amqp<2.0.0",
    "pika",
    "raven",
    "unidecode",
    # A library allowing to nest inlines in django admin.
    # Used in quizzes module for adding new quizzes.
    "django-nested-admin<3.4",
    # SIO2 dependencies:
    "filetracker>=2.1,<3.0",
    # Python 2 has class AppConf(metaclass=AppConfMetaClass):
    # SyntaxError: invalid syntax
    # when using newer version
    "django-appconf<1.0.4",
    # Dependencies from external sources live in requirements.txt
    # 0.5.13 suddenly requires django 2.2
    "django-simple-captcha==0.5.12",
    # HOTFIX
    "phonenumbers",
    # this is the last pdfminer.six version to support python2
    "pdfminer.six==20191110",
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
