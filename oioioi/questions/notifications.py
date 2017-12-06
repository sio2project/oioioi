from django.utils.translation import ugettext_noop

from oioioi.base.notification import NotificationHandler

# How many characters from a message will be passed to a notification
MAX_DETAILS_LENGTH = 60


def notification_function_answer(arguments):
    assert hasattr(arguments, 'user') \
            and hasattr(arguments, 'question_instance') \
            and hasattr(arguments, 'answer_instance'), \
            "The log doesn't have user, question_instance or answer_instance" \
            " value in the extra map"

    message_details = arguments.question_instance.topic + ': ' + \
            arguments.question_instance.content
    message = ugettext_noop("Your question was answered.")
    message_arguments = {'address': arguments.question_instance
            .get_absolute_url(),
            'details': message_details[:MAX_DETAILS_LENGTH]}

    NotificationHandler.send_notification(arguments.user,
        'question_answered', message, message_arguments)

NotificationHandler.register_notification('question_answered',
        notification_function_answer)


def notification_function_public(arguments):
    assert hasattr(arguments, 'contest') \
            and hasattr(arguments, 'message_instance'), \
            "The log doesn't have contest or message_instance value" \
            " in the extra map"

    message_details = arguments.message_instance.topic + ': ' + \
            arguments.message_instance.content
    message = ugettext_noop("New public message.")
    message_arguments = {
        'address': arguments.message_instance.get_absolute_url(),
        'details': message_details[:MAX_DETAILS_LENGTH]
    }

    controller = arguments.contest.controller

    for user in controller.users_to_receive_public_message_notification():
        NotificationHandler.send_notification(user,
            'new_public_message', message, message_arguments)

NotificationHandler.register_notification('new_public_message',
        notification_function_public)
