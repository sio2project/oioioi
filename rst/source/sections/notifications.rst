=============
Notifications
=============


Notifications in oioioi
-----------------------

To provide a user with an instant notification about some event,
we use an enriched Django logging mechanism.

A notification handler processes all incoming logs and analyzes
an extra dictionary passed alongside the log, looking for
a `notification` key.

If the value of the `notification` key is set and equal to the name of
one of the registered notification types, the notification is processed
by its own handler.

Notification handlers are functions, which analyze logs and notify
interested users about the log events. The handlers have to be registered
for each notification type in a file named `notifications.py` in an app.

Adding new notifications
------------------------

.. autoclass:: oioioi.base.notification.NotificationHandler
    :members: send_notification, register_notification

To add a new notification, you should:

* Check if the file notifications.py actually exists in your application.
  If so, you have to modify it, adding the code described below.
  Otherwise you should create it, remembering that:

  * You don't want to import django.utils.translation.gettext,
    as the notification message should be translated into
    the receiving user's language, not the sender's language. Instead,
    you may want to use gettext_noop function.
    This allows the external translating program to process these strings,
    but prevents translating them at a wrong time
    by the Django translations module.

  * Your file will be automatically processed when the NotificationHandler
    is loaded - so only when notifications are enabled.

* Create your own function handling an event, following the example::

    def notification_function_answer(arguments):
        assert hasattr(arguments, 'user') \
                and hasattr(arguments, 'question_instance') \
                and hasattr(arguments, 'answer_instance'), \
                "The log doesn't have user, question_instance" \
                "or answer_instance value in the extra map"

        message = gettext_noop("Your question was answered.")
        message_arguments = {'link': arguments.question_instance
                .get_absolute_url()}

        NotificationHandler.send_notification(arguments.user,
            'question_answered', message, message_arguments)

  For each user to be notified, the function ``send_notification``
  should be executed.

* Register it using :meth:`register_notification`
  in the body of notification.py file.

* Look into other `notifications.py` files for more examples.


Using notifications
-------------------

When a specified event occurs, a logging event should be called with
the `notification` value set to the name of the notification::

    logger.info('User %s has done something.', some_user,
        extra = {'notification' = 'user_has_done_something',
        'something_id' = something_id})

Additional parameters in the extra map should be specified by the handling
function in a notifications.py file.
