# -*- coding: utf-8 -*-

# pylint: disable=C0301
# Line too long

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os
import sys

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
        "Django>=1.5,<1.6",
        "pytz>=2013b",
        "South>=0.8.3,<2.0",
        "BeautifulSoup",
        "PyYAML",
        "python-dateutil",
        "django-nose",
        "django-registration>=1.0",
        "django-celery>=3.1.15",
        "django-supervisor",
        "linaro-django-pagination",
        "django-compressor",
        # Workaround for SIO-1266
        "django-grappelli==2.4.4",
        "pygments",

        "django-debug-toolbar",
        "django-extensions>=1.0.0",
        "werkzeug",

        # Old versions have buggy coverage reports generation, raising
        # an exception like this:
        #
        #  IOError: [Errno 13] Permission denied: '/usr/share/pyshared/PIL/__init__.py,cover'
        #
        "nose >= 1.1",

        "nose-capturestderr",
        "nose-html",
        "nose-profile",

        "fpdf",
        "pdfminer>=20110515,<20131113",
        "slate",
        "unicodecsv",

        "chardet",

        "django-gravatar2",

        # A library required by AMQP, used in notifications system.
        # We need version >= 1.5.1, becuase it has fixed this bug
        # https://github.com/celery/librabbitmq/issues/42
        "librabbitmq>=1.5.1",

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
        'http://github.com/sio2project/sioworkers/zipball/master#egg=sioworkers-1.0.dev',
        'http://github.com/sio2project/filetracker/zipball/master#egg=filetracker-1.0.dev',
        'http://github.com/mitsuhiko/werkzeug/zipball/master#egg=Werkzeug-dev',
        'http://bitbucket.org/mdebski/django-output-validator-1.5/get/django-1.5.zip#egg=django-output-validator-1.5md1',
    ],

    entry_points={
        'console_scripts': [
            'django-staticfiles-lessc = oioioi.base.lessc:main',
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
