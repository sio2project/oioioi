from django.contrib.auth.models import User
from django.db import transaction
from oioioi.gamification.models import FriendProxy, FriendshipRequest


class UserFriends(object):
    """ A class for managing friendships in which the given user is involved.
    """
    def __init__(self, user):
        self._user = user
        self._proxy, _ = FriendProxy.objects.get_or_create(user=user)

    def _add_friend(self, user):
        self._proxy.friends.add(UserFriends(user)._proxy)

    @transaction.atomic
    def send_friendship_request(self, user):
        """ Sends a friendship request to the specified user.

            If the specified user sent request to this user too,
            friendship is estabilished between the users automatically.
            Throws ValueError when trying to send request to oneself, if
            this request was sent already or if the users are already friends.
        """
        if self._user == user:
            raise ValueError("Cannot send a friendship request to oneself")

        if self.is_friends_with(user):
            raise ValueError("Users are already friends")

        other_proxy = UserFriends(user)._proxy
        try:
            mirrored = self._proxy.incoming_requests.get(sender=other_proxy)
            self.accept_friendship_request(mirrored)

        except FriendshipRequest.DoesNotExist:
            _, created = FriendshipRequest.objects.get_or_create(
                                          sender=self._proxy,
                                          recipient=other_proxy)
            if not created:
                raise ValueError("Friendship request already sent")

    @transaction.atomic
    def accept_friendship_request(self, request):
        """ Accepts a friendship request directed towards the user.

            Its sender and recipient become friends afterwards.
            Throws ValueError if the user is not the request's recipient.
        """
        if request.recipient.user != self._user:
            raise ValueError("User is not the request's recipient")

        request.delete()
        self._add_friend(request.sender.user)

    def refuse_friendship_request(self, request):
        """ Refuses a friendship request directed towards the user.

            Throws ValueError if the user is not the request's recipient.
        """
        if request.recipient.user != self._user:
            raise ValueError("User is not the request's recipient")

        request.delete()

    def remove_friend(self, user):
        """ Removes a friendship between this and the specified user.

            Throws ValueError if the users are not friends.
        """
        other_proxy = UserFriends(user)._proxy
        if not self._proxy.friends.filter(pk=other_proxy.pk).exists():
            raise ValueError("Users are not friends")

        self._proxy.friends.remove(other_proxy)

    def is_friends_with(self, user):
        """Returns if this and the given user are friends."""
        return self.friends.filter(pk=user.pk).exists()

    @property
    def my_requests(self):
        """ Queryset of unresolved (neither accepted nor refused) requests
            sent by this user.
        """
        return self._proxy.sent_requests

    @property
    def requests_for_me(self):
        """Queryset of unresolved requests sent to this user."""
        return self._proxy.incoming_requests

    @property
    def friends(self):
        """Queryset of friends of this user."""
        return User.objects.filter(friendproxy__friends=self._proxy)
