import logging
from oioioi.base.utils.loaders import load_modules

class NotificationHandler(logging.StreamHandler):
    """This handler will catch all logs and emit a notification
       if a notification type is set in extra dictionary, in log record.

       Example usage is in external documentation.
    """

    loaded_notifications = False

    @staticmethod
    def send_notification(user_id, notification_type, notification_message):
        """This function will send a notification for a specified person.
           It will be done by sending a message to RabbitMQ.
        """
        pass

    @staticmethod
    def register(notification_type, notification_function):
        """Register a specific notification handler function for
           specified type of notification, that will be executed
           each time the log with this notification type will be
           processed.
        """
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

        if not NotificationHandler.loaded_notifications:
            load_modules('notifications')
            NotificationHandler.loaded_notifications = True

        if hasattr(record, 'notification'):
            pass
        else:
            pass

