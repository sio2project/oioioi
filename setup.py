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
    "django-supervisor==0.4.0",
    "supervisor>=4.0,<4.3",
    "enum34>=1.1,<1.2",
    # http://stackoverflow.com/questions/31417964/importerror-cannot-import-name-wraps
    # ¯\_(ツ)_/¯
    "mock==1.0.1",
]

python3_specific_requirements = []

python23_universal_requirements = [
    "Django>=1.11,<1.12",  # when upgrading, upgrade also django-two-factor-auth!
    "pytz>=2013b,<=2021.1",
    "sqlalchemy<1.5",
    # latest version of django-otp for Django 1.10 and django-two-factor-auth 1.6.*
    "django-otp>=0.4.3,<0.5",
    "beautifulsoup4<4.10",
    "PyYAML<5.5",
    "python-dateutil<2.9",
    "django-two-factor-auth<1.7",  # latest version for Django 1.10
    "django-formtools<2.2", # latest version for Django 1.10
    # and django-two-factor-auth 1.6.*; django-formtools<2.2 can be removed
    # after migration to Django 1.11
    "django-registration-redux>=1.6,<2.0",  # latest for Django 1.10
    "Celery==4.4.7",
    "coreapi>=2.3.0,<2.4",
    "dj-pagination>=2.3.3.final.0",
    "django-compressor==2.2",  # latest version
    "pygments<2.6",
    "django-libsass>=0.7,<=0.8",
    "django-debug-toolbar>=1.9.1,<1.10",  # latest version for Django 1.10
    "django-extensions>=2.2.9,<3.0",  # latest version for Django 1.11
    "djangorestframework==3.8.2",  # latest version for Django 1.10
    'pytest==4.6.11',
    'pytest-django==3.10.0',
    'pytest-html==1.22.1',
    'pytest-xdist==1.34.0',
    'pytest-cov>=2.11,<2.12',
    'requests<3',
    "fpdf<1.8",
    "unicodecsv<0.15",
    "dnslib<0.10",
    "bleach>=3.1.0,<3.2",
    "chardet<4.1",
    "django-gravatar2<1.5",
    "django-mptt>=0.8.7,<0.9.1",  # latest version for Django 1.11, supports 2.0
    "mistune<0.9",
    "amqp<2.7,>=2.6.0",
    "pika<1.3",
    "sentry-sdk",
    "unidecode<1.3",
    # A library allowing to nest inlines in django admin.
    # Used in quizzes module for adding new quizzes.
    "django-nested-admin<3.4",
    # SIO2 dependencies:
    "filetracker>=2.1.5,<3.0",
    # Dependencies from external sources live in requirements.txt
    # 0.5.13 suddenly requires django 2.2
    "django-simple-captcha==0.5.12",
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
