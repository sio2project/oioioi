from oioioi.contests.controllers import ContestController


class LivedataContestControllerMixin:
    """ContestController mixin that sets a default setting for livedata
    visibility.
    """

    def can_see_livedata(self, request):
        return False


ContestController.mix_in(LivedataContestControllerMixin)
