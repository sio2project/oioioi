from oioioi.base.permissions import make_request_condition


@make_request_condition
def can_see_livedata(request):
    return request.contest.controller.can_see_livedata(request)


def get_display_name(user):
    if user.last_name and user.first_name:
        return f"{user.first_name[0]}. {user.last_name}"
    else:
        return user.username
