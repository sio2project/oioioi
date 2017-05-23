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
        # Django < 1.8.15 is vulnerable to CSRF when used with Google Analytics:
        # https://www.djangoproject.com/weblog/2016/sep/26/security-releases/
        "Django>=1.8.15,<1.9",
        "pytz>=2013b",
        "sqlalchemy",
        "BeautifulSoup",
        "PyYAML",
        "python-dateutil",
        # Earlier versions of django-nose are incompatible with Django 1.8
        "django-nose>=1.4",
        "nose-picker>=0.5.3",

        "django-registration-redux>=1.6",

        "Celery>=3.1.15,<4.0.0",
        "django-celery>=3.1.15,<=3.1.17",
        "django-supervisor",
        "linaro-django-pagination",
        "django-compressor>=1.4,<1.6",
        # https://github.com/sehmaschine/django-grappelli/issues/659
        "django-grappelli==2.8.2",
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

        "django-mptt<0.8.0",

        "mistune",

        # Some of celery dependencies (kombu) require amqp to be <2.0.0
        "amqp<2.0.0",

        # A library required by AMQP, used in notifications system.
        # We need version >= 1.5.1, becuase it has fixed this bug
        # https://github.com/celery/librabbitmq/issues/42
        "librabbitmq>=1.5.1",

        "raven",

        # Dependencies from external sources live in requirements.txt
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='oioioi.runtests.runtests',

    # Well, dependency_links is deprecated in pip and setuptools. We leave
    # it for some time, though. You should install oioioi using
    #
    # $ pip install -r requirements.txt
    #
    dependency_links=[
        'http://github.com/sio2project/sioworkers/zipball/master#egg=sioworkers-1.3',
        'http://github.com/sio2project/filetracker/zipball/master#egg=filetracker-1.1.0',
        'http://github.com/mitsuhiko/werkzeug/zipball/master#egg=Werkzeug-dev',
        'http://github.com/sio2project/linaro-django-pagination/zipball/master#egg=linaro-django-pagination',
    ],

    entry_points={
        'console_scripts': [
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
