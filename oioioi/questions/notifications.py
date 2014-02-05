from oioioi.base.notification import NotificationHandler


# We want to mark message strings to be extracted to translate
# and not translate them in this module.
_ = lambda s: s


def notification_function_answer(arguments):
    assert hasattr(arguments, 'user') \
            and hasattr(arguments, 'question_instance') \
            and hasattr(arguments, 'answer_instance'), \
            "The log doesn't have user, question_instance or answer_instance" \
            " value in the extra map"

    message = _("Your question was answered.")
    message_arguments = {'link': arguments.question_instance
            .get_absolute_url()}

    NotificationHandler.send_notification(arguments.user,
        'question_answered', message, message_arguments)

NotificationHandler.register_notification('question_answered',
        notification_function_answer)


def notification_function_public(arguments):
    assert hasattr(arguments, 'contest') \
            and hasattr(arguments, 'message_instance'), \
            "The log doesn't have contest or message_instance value" \
            " in the extra map"

    message = _("New public message.")
    message_arguments = {'link': arguments.message_instance.get_absolute_url()}

    controller = arguments.contest.controller

    for user in controller.users_to_receive_public_message_notification():
        NotificationHandler.send_notification(user,
            'new_public_message', message, message_arguments)

NotificationHandler.register_notification('new_public_message',
        notification_function_public)
