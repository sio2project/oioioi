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
    "Django>=5.2,<5.3",
    "pytz>=2023.3,<2023.4",
    "SQLAlchemy<2.1.0",
    "beautifulsoup4>=4.12,<4.13",
    "PyYAML>=6.0.1,<6.1",
    "python-dateutil>=2.8,<2.9",
    "django-two-factor-auth>=1.15,<1.16",
    "django-formtools>=2.4,<2.5",
    "django-registration-redux>=2.12,<2.13",
    "Celery<5.4.0",
    "coreapi>=2.3,<2.4",
    "dj-pagination>=2.5,<2.6",
    "django-compressor>=4.5,<4.6",
    "Pygments>=2.15,<2.16",
    "django-libsass>=0.9,<0.10",
    "django-debug-toolbar",
    "django-extensions>=3.2,<3.3",
    "djangorestframework>=3.14,<3.15",
    "Werkzeug",
    "pytest>=7.2,<8.0",
    "pytest-cov>=4.0,<5.0",
    "pytest-django>=4.11,<5.0",
    "pytest-html>=3.1,<4.0",
    "pytest-metadata>=3.0,<4.0",
    "pytest-xdist>=3.2,<4.0",
    "requests>=2.31,<2.32",
    "fpdf>=1.7,<1.8",
    "unicodecsv>=0.14,<0.15",
    "dnslib>=0.9,<0.10",
    "bleach>=6.0,<6.1",
    "chardet>=5.1,<5.2",
    "django-gravatar2>=1.4,<1.5",
    "django-mptt>=0.16,<0.17",
    "mistune<2.0",   # 2.0 is breaking
    "pika>=1.3,<1.4",
    "Unidecode>=1.3,<1.4",
    "sentry-sdk>=2.16.0,<2.17.0",
    "fontawesomefree>=6.4,<6.5",
    # A library allowing to nest inlines in django admin.
    # Used in quizzes module for adding new quizzes.
    "django-nested-admin>=4.1,<4.2",
    # Library for parsing dates and timedelta
    "humanize<=4.9.0",
    # SIO2 dependencies:
    "filetracker>=2.2.0,<3.0",
    "django-simple-captcha>=0.5,<=0.5.18",
    "phonenumbers>=8.13,<8.14",
    "pdfminer.six==20221105",
    # https://stackoverflow.com/questions/73929564/entrypoints-object-has-no-attribute-get-digital-ocean
    "importlib-metadata<5.0",
    "supervisor<4.3",  # previously http://github.com/Supervisor/supervisor/zipball/master#egg=supervisor==4.0.0.dev0
    "django-supervisor@git+https://github.com/sio2project/django-supervisor#egg=django-supervisor",  # previously http://github.com/badochov/djsupervisor/zipball/master#egg=djsupervisor==0.4.0
    "socketify>=0.0.31,<0.0.32",
    "aio-pika>=9.5.5,<10.0.0",
    "aiohttp>=3.12.2,<4.0.0",
    "cachetools>=6.0.0,<7.0.0",
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
