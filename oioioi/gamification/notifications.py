from django.utils.translation import ugettext_noop
from django.core.urlresolvers import reverse
from oioioi.base.notification import NotificationHandler


TYPE_TO_TEXT = {
    'sent': ugettext_noop("User %(sender)s has "
                            "sent you a friendship request."),
    'accepted': ugettext_noop("User %(sender)s has "
                            "accepted your friendship request."),
    'refused': ugettext_noop("User %(sender)s "
                            "refused your friendship request."),
    'ended': ugettext_noop("User %(sender)s no longer "
                            "wants to be your friend."),
}


def friendship_notification(arguments):
    assert hasattr(arguments, 'type') \
            and hasattr(arguments, 'sender') \
            and hasattr(arguments, 'recipient'), \
            "The log doesn't have type, sender or recipient " \
            "value in the extra map"

    link_target_user = arguments.sender
    notification_recipient = arguments.recipient

    url = reverse('view_profile',
                  kwargs={'username': link_target_user.username})

    message_arguments = {
        'sender': arguments.sender.username,
        'recipient': arguments.recipient.username,
        'address': url
    }

    message = TYPE_TO_TEXT[arguments.type]

    NotificationHandler.send_notification(notification_recipient,
                        'friends', message, message_arguments)

NotificationHandler.register_notification('friends', friendship_notification)
