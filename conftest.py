from __future__ import print_function
import pytest


def pytest_addoption(parser):
    parser.addoption('--runslow', action='store_true',
                     default=False, help="run slow tests")


# called for running each test
def pytest_runtest_setup(item):
    from oioioi.contests.tests import pytest_plugin as contests_plugin
    from oioioi.base.tests import pytest_plugin as base_plugin
    contests_plugin.pytest_runtest_setup(item)
    base_plugin.pytest_runtest_setup(item)


def pytest_collection_modifyitems(config, items):
    # --runslow flag: do not skip slow tests
    if config.getoption('--runslow', False):
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


# Removing links column from html report
@pytest.mark.optionalhook
def pytest_html_results_table_header(cells):
    cells.pop()


# Removing links column from html report
@pytest.mark.optionalhook
def pytest_html_results_table_row(report, cells):
    cells.pop()
