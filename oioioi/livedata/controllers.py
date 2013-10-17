from oioioi.contests.controllers import ContestController


class LivedataContestControllerMixin(object):
    def can_see_livedata(self, request):
        return False

ContestController.mix_in(LivedataContestControllerMixin)
