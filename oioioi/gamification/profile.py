from django.template.loader import render_to_string
from oioioi.base.menu import OrderedRegistry
from oioioi.gamification.friends import UserFriends


profile_registry = OrderedRegistry()


def profile_section(order):
    """ Decorator for registering profile view sections.

        The decorated function is passed the request and shown user.
        It may return a string, a TemplateResponse or HttpResponseRedirect.
    """
    return profile_registry.register_decorator(order)


@profile_section(order=99)
def friend_finder_section(request, user):
    if user != request.user:
        return ''

    return render_to_string('gamification/profile/invite-friends.html')


@profile_section(order=100)
def friend_list_section(request, user):
    if user != request.user:
        return ''

    return render_to_string('gamification/profile/friends-list.html',
            {'friends': UserFriends(user).friends})
