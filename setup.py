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

# Requirements moved to requirements.in (compiled to requirements_pinned.txt)
requirements = []

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
