import logging


class NotificationHandler(logging.StreamHandler):
    """This handler will catch all logs and emit a notification
       if a notification type is set in extra dictionary, in log record.

       Example usage is in external documentation.
    """
    # This dictionary stores functions handling registered notifications
    notification_functions = {}

    @classmethod
    def send_notification(cls, user_id, notification_type, \
            notification_message):
        """This function will send a notification for a specified person.
           It will be done by sending a message to RabbitMQ.
        """
        pass

    @classmethod
    def register(cls, notification_type, notification_function):
        """Register a specific notification handler function for
           specified type of notification, that will be executed
           each time the log with this notification type will be
           processed.
        """
        cls.notification_functions[notification_type] = notification_function
        pass

    def emit(self, record):
        """This function is called each time a  message is logged.

           In our design, it's role is to invoke a specific handler
           for corresponding notification type, registered before
           via :meth:`register` function by caller.

           Specific notification handler should prepare translated
           message string, split one event for particular users
           and execute :meth:`send_notification` function for each user
           who should be notified.
        """

        #
        # Emit is called with a lock held, see
        # http://docs.python.org/2/library/logging.html#logging.Handler.handle
        #

        if hasattr(record, 'notification'):
            notification_type = getattr(record, 'notification')
            if notification_type in NotificationHandler.notification_functions:
                notification_function = NotificationHandler\
                    .notification_functions[notification_type]
                notification_function(record)
            else:
                print "Tried to handle a non-existent notification"
        else:
            pass

