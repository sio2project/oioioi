from nose.plugins import Plugin

from oioioi.contests.current_contest import set_cc_id


class ClearCurrentContest(Plugin):
    name = "clearcc"
    enabled = True

    def startTest(self, test):
        set_cc_id(None)
