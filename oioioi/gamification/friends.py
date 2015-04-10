import logging

from django.contrib.auth.models import User
from django.db import transaction
from django.dispatch import receiver, Signal
from oioioi.gamification.models import FriendProxy, FriendshipRequest


# "sender" is the user performing action, "recipient" is the user
# on which the action is performed (e.g. sender=user1 accepts friendship
# from recipient=user2)
FriendshipRequestSent = Signal(providing_args=['sender', 'recipient'])
FriendshipRequestAccepted = Signal(providing_args=['sender', 'recipient'])
FriendshipRequestRefused = Signal(providing_args=['sender', 'recipient'])
FriendshipEnded = Signal(providing_args=['sender', 'recipient'])

logger = logging.getLogger(__name__)


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

            FriendshipRequestSent.send(sender=self._user, recipient=user)

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

        FriendshipRequestAccepted.send(sender=request.recipient.user,
                                       recipient=request.sender.user)

    def refuse_friendship_request(self, request):
        """ Refuses a friendship request directed towards the user.

            Throws ValueError if the user is not the request's recipient.
        """
        if request.recipient.user != self._user:
            raise ValueError("User is not the request's recipient")

        request.delete()
        FriendshipRequestRefused.send(sender=request.recipient.user,
                                      recipient=request.sender.user)

    def remove_friend(self, user):
        """ Removes a friendship between this and the specified user.

            Throws ValueError if the users are not friends.
        """
        if not self.is_friends_with(user):
            raise ValueError("Users are not friends")

        other_proxy = UserFriends(user)._proxy
        self._proxy.friends.remove(other_proxy)

        FriendshipEnded.send(sender=self._user, recipient=user)

    def is_friends_with(self, user):
        """Returns if this and the given user are friends."""
        return self.friends.filter(pk=user.pk).exists()

    @property
    def my_requests(self):
        """ Queryset of unresolved (neither accepted nor refused) requests
            sent by this user.
        """
        return self._proxy.sent_requests

    def my_request_for(self, recipient):
        """ Returns a request from this user to the recipient.

            If it does not exist, it throws FriendshipRequest.DoesNotExist.
        """
        return self.my_requests.get(recipient__user=recipient)

    def sent_request_to(self, recipient):
        """Returns if this user has sent a request for the recipient."""
        return self.my_requests.filter(recipient__user=recipient).exists()

    @property
    def requests_for_me(self):
        """Queryset of unresolved requests sent to this user."""
        return self._proxy.incoming_requests

    def request_from(self, sender):
        """ Returns a request from the sender to this user.

            If it does not exist, it throws FriendshipRequest.DoesNotExist.
        """
        return self.requests_for_me.get(sender__user=sender)

    def has_request_from(self, sender):
        """Returns if this user has an incoming request from the sender."""
        return self.requests_for_me.filter(sender__user=sender).exists()

    @property
    def friends(self):
        """Queryset of friends of this user."""
        return User.objects.filter(friendproxy__friends=self._proxy)


def base_notification_handler(sender, recipient, type, text):
    logger.info(text,
                {'sender': sender, 'recipient': recipient},
                extra={'notification': 'friends',
                       'type': type,
                       'sender': sender,
                       'recipient': recipient})


@receiver(FriendshipRequestSent, dispatch_uid='friendship_notification')
def friendship_request_sent_notification(sender, recipient, **kwargs):
    base_notification_handler(sender, recipient, 'sent',
                              'User %(sender)s sent a '
                              'friendship request to %(recipient)s.')


@receiver(FriendshipRequestAccepted, dispatch_uid='friendship_notification')
def friendship_request_accepted_notification(sender, recipient, **kwargs):
    base_notification_handler(sender, recipient, 'accepted',
                              'User %(sender)s accepted '
                              'friendship request from %(recipient)s.')


@receiver(FriendshipRequestRefused, dispatch_uid='friendship_notification')
def friendship_request_refused_notification(sender, recipient, **kwargs):
    base_notification_handler(sender, recipient, 'refused',
                              'User %(sender)s refused '
                              'friendship request from %(recipient)s.')


@receiver(FriendshipEnded, dispatch_uid='friendship_notification')
def friendship_ended_notification(sender, recipient, **kwargs):
    base_notification_handler(sender, recipient, 'ended',
                              'User %(sender)s ended '
                              'friendship with %(recipient)s.')
