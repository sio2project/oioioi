from django.core.cache import cache


# called for running each test
def pytest_runtest_setup(item):
    cache.clear()
