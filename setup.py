# -*- coding: utf-8 -*-

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
    version = '0.1.1.dev',
    description='The web frontend of the SIO2 Project contesting system',
    author='The SIO2 Team',
    author_email='sio2@sio2project.mimuw.edu.pl',
    url='http://sio2project.mimuw.edu.pl',
    install_requires=[
        "Django>=1.5,<1.6",
        "pytz>=2013b",
        "South>=0.8.2.1accek,<2.0",
        "BeautifulSoup",
        "PyYAML",
        "django-nose",
        "django-registration>=1.0",
        "django-celery",
        "django-supervisor",
        "linaro-django-pagination",
        # Workaround for SIO-1266
        "django-grappelli==2.4.4",
        "django-compressor",
        "pygments",

        "django-debug-toolbar",
        "django-extensions>=1.0.0",
        "django-output-validator>=1.5md1",
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

        "filetracker>=1.0.dev",
        "sioworkers>=0.92",

        "fpdf",
        "pdfminer>=20110515",
        "slate",
        "unicodecsv",

        "chardet",

        "django-gravatar2",
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='oioioi.runtests.runtests',
    dependency_links=[
        'http://github.com/sio2project/filetracker/zipball/master#egg=filetracker-1.0.dev',
        'http://github.com/mitsuhiko/werkzeug/zipball/master#egg=Werkzeug-dev',
        'http://bitbucket.org/mdebski/django-output-validator-1.5/get/django-1.5.zip#egg=django-output-validator-1.5md1',
        'http://bitbucket.org/accek/south/get/accek-alternate-version-string.tar.gz#egg=South-0.8.2.1accek',
    ],
    entry_points = {
        'console_scripts': [
            'django-staticfiles-lessc = oioioi.base.lessc:main',
            'oioioi-create-config = oioioi.deployment.create_config:main',
        ],
    },
)
