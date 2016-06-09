from oioioi.base.permissions import make_request_condition


@make_request_condition
def can_see_livedata(request):
    return request.contest.controller.can_see_livedata(request)
