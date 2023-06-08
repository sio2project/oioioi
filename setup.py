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
"amqp==2.6.1"
"asgiref==3.7.2"
"attrs==23.1.0"
"Automat==22.10.0"
"backports.zoneinfo==0.2.1"
"beautifulsoup4==4.12.2"
"billiard==3.6.4.0"
"black==22.3.0"
"bleach==6.0.0"
"bsddb3==6.2.7"
"celery==4.4.7"
"certifi==2023.5.7"
"cffi==1.15.1"
"chardet==5.1.0"
"charset-normalizer==3.1.0"
"click==8.1.3"
"click-didyoumean==0.3.0"
"click-repl==0.2.0"
"constantly==15.1.0"
"coreapi==2.3.3"
"coreschema==0.0.4"
"coverage==7.2.7"
"cryptography==41.0.1"
"dj-pagination==2.5.0"
"Django==4.2.2"
"django-appconf==1.0.5"
"django-compressor==4.3.1"
"django-debug-toolbar==4.1.0"
"django-extensions==3.2.3"
"django-formtools==2.4.1"
"django-gravatar2==1.4.4"
"django-js-asset==2.0.0"
"django-libsass==0.9"
"django-mptt==0.14.0"
"django-nested-admin==4.0.2"
"django-otp==1.2.1"
"django-phonenumber-field==6.4.0"
"django-ranged-response==0.2.0"
"django-registration-redux==2.12"
"django-simple-captcha==0.5.17"
"django-supervisor @ git+https://github.com/sio2project/django-supervisor@57c1932fbf06a3118ee44eb12d518105059e2e28"
"django-two-factor-auth==1.15.2"
"djangorestframework==3.14.0"
"dnslib==0.9.23"
"ecs-logging==2.0.2"
"elastic-apm==6.16.1"
"exceptiongroup==1.1.1"
"execnet==1.9.0"
"filetracker==2.1.5"
"flup6==1.1.1"
"fontawesomefree==6.4.0"
"fpdf==1.7.2"
"gevent==1.3.1"
"greenlet==0.4.13"
"gunicorn==19.9.0"
"hyperlink==21.0.0"
"idna==3.4"
"importlib-metadata==6.6.0"
"incremental==22.10.0"
"iniconfig==2.0.0"
"isort==5.6.4"
"itypes==1.2.0"
"Jinja2==3.1.2"
"kombu==4.6.11"
"libsass==0.22.0"
"MarkupSafe==2.1.3"
"mistune==0.8.4"
"mypy-extensions==1.0.0"
"packaging==23.1"
"pathspec==0.11.1"
"pdfminer.six==20221105"
"phonenumbers==8.13.13"
"pika==1.3.2"
"Pillow==9.5.0"
"platformdirs==3.5.1"
"pluggy==1.0.0"
"progressbar2==4.2.0"
"prompt-toolkit==3.0.38"
"psycopg2-binary==2.8.6"
"py==1.11.0"
"pycparser==2.21"
"Pygments==2.15.1"
"PyHamcrest==2.0.4"
"pypng==0.20220715.0"
"pytest==7.3.1"
"pytest-cov==4.1.0"
"pytest-django==4.5.2"
"pytest-html==3.2.0"
"pytest-metadata==3.0.0"
"pytest-xdist==3.3.1"
"python-dateutil==2.8.2"
"python-memcached==1.59"
"python-monkey-business==1.0.0"
"python-utils==3.6.0"
"pytz==2023.3"
"PyYAML==6.0"
"qrcode==7.4.2"
"raven==6.10.0"
"rcssmin==1.1.1"
"requests==2.31.0"
"rjsmin==1.2.1"
"sentry-sdk==1.25.1"
"shortuuid==1.0.11"
"simplejson==3.14.0"
"sioworkers @ http://github.com/sio2project/sioworkers/archive/refs/tags/v1.4.2.tar.gz"
"six==1.16.0"
"sortedcontainers==2.1.0"
"soupsieve==2.4.1"
"SQLAlchemy==2.0.15"
"sqlparse==0.4.4"
"supervisor==4.2.5"
"tomli==2.0.1"
"Twisted==20.3.0"
"typing_extensions==4.6.3"
"tzdata==2023.3"
"unicodecsv==0.14.1"
"Unidecode==1.3.6"
"uritemplate==4.1.1"
"urllib3==1.26.16"
"uWSGI==2.0.21"
"vine==1.3.0"
"watchdog==2.3.1"
"wcwidth==0.2.6"
"webencodings==0.5.1"
"Werkzeug==2.3.5"
"wrapt==1.15.0"
"zipp==3.15.0"
"zope.interface==6.0"
]

# All modules in the newest versions at the time of upgrade to Django 4.2
# unless specified otherwise.
requirements = [
    "Django==4.2.2",
    "pytz==2023.3",
    "SQLAlchemy==2.0.15",
    "beautifulsoup4==4.12.2",
    "PyYAML==6.0",
    "python-dateutil==2.8.2",
    "django-two-factor-auth==1.15.2",
    "django-formtools==2.4.1",
    "django-registration-redux==2.12",
    "Celery==4.4.7",    # 5.0 is breaking
    "coreapi==2.3.3",
    "dj-pagination==2.5.0",
    "django-compressor==4.3.1",
    "Pygments==2.15.1",
    "django-libsass==0.9",
    "django-debug-toolbar==4.1.0",
    "django-extensions==3.2.3",
    "djangorestframework==3.14.0",
    "Werkzeug==2.3.5",
    "pytest==7.3.1",
    "pytest-cov==4.1.0",
    "pytest-django==4.5.2",
    "pytest-html==3.2.0",
    "pytest-metadata==3.0.0",
    "pytest-xdist==3.3.1",
    "requests==2.31.0",
    "fpdf==1.7.2",
    "unicodecsv==0.14.1",
    "shortuuid==1.0.11",
    "dnslib==0.9.23",
    "bleach==6.0.0",
    "chardet==5.1.0",
    "django-gravatar2==1.4.4",
    "django-mptt==0.14.0",
    "mistune<2.0",   # 2.0 is breaking
    "pika==1.3.2",
    "raven==6.10.0",
    "Unidecode==1.3.6",
    "sentry-sdk==1.25.1",
    "fontawesomefree==6.4.0",
    # A library allowing to nest inlines in django admin.
    # Used in quizzes module for adding new quizzes.
    "django-nested-admin==4.0.2",
    # SIO2 dependencies:
    "filetracker>=2.1.5,<3.0",
    "django-simple-captcha>=0.5.16,<=0.5.18",
    "phonenumbers==8.13.13",
    "pdfminer.six==20221105",
    # https://stackoverflow.com/questions/73929564/entrypoints-object-has-no-attribute-get-digital-ocean
    "importlib-metadata<5.0",
    "supervisor<4.3",  # previously http://github.com/Supervisor/supervisor/zipball/master#egg=supervisor==4.0.0.dev0
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
