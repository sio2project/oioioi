from oioioi.contests.current_contest import set_cc_id


# called for running each test
def pytest_runtest_setup(item):
    set_cc_id(None)
