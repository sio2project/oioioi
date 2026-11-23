import pytest
from django.conf import settings
from django.utils import translation
from oioioi.base.tests import pytest_plugin as base_plugin
from oioioi.contests.tests import pytest_plugin as contests_plugin
import shutil

def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")
    parser.addoption("--strict-template-vars", action="store_true", help="Raise errors for undefined template variables")
    parser.addoption("--require-latex", action="store_true", default=False, help="fail tests needing latex if pdflatex is missing")


# called for running each test
def pytest_runtest_setup(item):
    contests_plugin.pytest_runtest_setup(item)
    base_plugin.pytest_runtest_setup(item)


def pytest_configure(config):
    if config.getoption("--strict-template-vars"):
        # this will raise an error if a template variable is not defined
        settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = "{% templatetag openvariable %} INVALID_VAR: %s {% templatetag closevariable %}"


def pytest_collection_modifyitems(config, items):
    skip_slow = not config.getoption("--runslow", False)
    require_latex = config.getoption("--require-latex", False)

    has_pdflatex = shutil.which("pdflatex") is not None

    slow_marker = pytest.mark.skip(reason="need --runslow option to run")

    latex_marker = latex_marker = pytest.mark.skip(reason="pdflatex is not installed")
    if require_latex:  # if flag --require-latex exists
        latex_marker = pytest.mark.xfail(run=False, strict=True, reason="pdflatex required but not found")

    for item in items:
        if skip_slow and "slow" in item.keywords:
            item.add_marker(slow_marker)

        if not has_pdflatex and "needs_latex" in item.keywords:
            item.add_marker(latex_marker)

# Removing links column from html report
@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.pop()


# Removing links column from html report
@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    cells.pop()


@pytest.fixture()
def require_migrations_flag(request):
    config = request.config
    nomigrations_enabled_flag = config.getoption("nomigrations")

    if nomigrations_enabled_flag:
        pytest.skip("Test requires the --migrations flag to run.")


@pytest.fixture(autouse=True)
def reset_active_language():
    # Middleware activates the request's language (e.g. from the lang cookie)
    # in the test thread and nothing resets it, so it would leak into later tests.
    yield
    translation.deactivate()
