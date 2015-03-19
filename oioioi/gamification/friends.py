class UserFriends(object):
    """ A class for managing friendships in which the given user is involved.
    """
    def __init__(self, user):
        raise NotImplementedError

    def send_friendship_request(self, user):
        """ Sends a friendship request to the specified user.

            If the specified user sent request to this user too,
            friendship is estabilished between the users automatically.
            Throws ValueError when trying to send request to oneself, or
            if the users are already friends.
        """
        raise NotImplementedError

    def accept_friendship_request(self, request):
        """ Accepts a friendship request directed towards the user.

            Its sender and recipent become friends afterwards.
            Throws ValueError if the user is not the request's recipent.
        """
        raise NotImplementedError

    def refuse_friendship_request(self, request):
        """ Refuses a friendship request directed towards the user.

            Throws ValueError if the user is not the request's recipent.
        """
        raise NotImplementedError

    def remove_friend(self, user):
        """ Removes a friendship between this and the specified user.

            Throws ValueError if the users are not friends.
        """
        raise NotImplementedError

    def is_friends_with(self, user):
        """Returns if this and the given user are friends."""
        raise NotImplementedError

    @property
    def my_requests(self):
        """ Queryset of unresolved (neither accepted nor refused) requests
            sent by this user.
        """
        raise NotImplementedError

    @property
    def requests_for_me(self):
        """Queryset of unresolved requests sent to this user."""
        raise NotImplementedError

    @property
    def friends(self):
        """Queryset of friends of this user."""
        raise NotImplementedError
