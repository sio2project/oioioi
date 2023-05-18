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

requirements = [
    "Django",
    "pytz",
    "sqlalchemy",
    "beautifulsoup4",
    "PyYAML",
    "python-dateutil",
    "django-two-factor-auth",
    "django-formtools",
    "django-registration-redux",
    "Celery",
    "coreapi",
    "dj-pagination",
    "django-compressor",
    "pygments",
    "django-libsass",
    "django-debug-toolbar",
    "django-extensions",
    "djangorestframework",
    "werkzeug",
    'pytest',
    'pytest-metadata',
    'pytest-django',
    'pytest-html',
    'pytest-xdist',
    'pytest-cov',
    'requests',
    "fpdf",
    "unicodecsv",
    "shortuuid",
    "dnslib",
    "bleach",
    "chardet",
    "django-gravatar2",
    "django-mptt",
    "mistune",
    "pika",
    "raven",
    "unidecode",
    "sentry-sdk",
    "fontawesomefree",
    # A library allowing to nest inlines in django admin.
    # Used in quizzes module for adding new quizzes.
    "django-nested-admin",
    # SIO2 dependencies:
    "filetracker",
    "django-simple-captcha",
    "phonenumbers",
    "supervisor",  # previously http://github.com/Supervisor/supervisor/zipball/master#egg=supervisor==4.0.0.dev0
    "django-supervisor@git+https://github.com/sio2project/django-supervisor#egg=django-supervisor",  # previously http://github.com/badochov/djsupervisor/zipball/master#egg=djsupervisor==0.4.0
]

setup(
    name='oioioi',
    version='0.2.0.dev',
    description='The web frontend of the SIO2 Project contesting system',
    author='The SIO2 Team',
    author_email='sio2@sio2project.mimuw.edu.pl',
    url='http://sio2project.mimuw.edu.pl',
    install_requires=requirements,
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='oioioi.runtests.runtests',
    entry_points={
        'console_scripts': [
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
