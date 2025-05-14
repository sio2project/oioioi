from __future__ import print_function

import pytest

from oioioi.base.tests import pytest_plugin as base_plugin
from oioioi.contests.tests import pytest_plugin as contests_plugin
from django.conf import settings


def pytest_addoption(parser):
    parser.addoption(
        '--runslow', action='store_true', default=False, help="run slow tests"
    )
    parser.addoption(
        '--strict-template-vars', action='store_true', help="Raise errors for undefined template variables")


# called for running each test
def pytest_runtest_setup(item):
    contests_plugin.pytest_runtest_setup(item)
    base_plugin.pytest_runtest_setup(item)


def pytest_configure(config):
    if config.getoption("--strict-template-vars"):
        # this will raise an error if a template variable is not defined
        settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'] = '{% templatetag openvariable %} INVALID_VAR: %s {% templatetag closevariable %}'
        

def pytest_collection_modifyitems(config, items):
    # --runslow flag: do not skip slow tests
    if config.getoption('--runslow', False):
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


# Removing links column from html report
@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.pop()


# Removing links column from html report
@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    cells.pop()
