import logging
from oioioi.base.utils.loaders import load_modules

logger = logging.getLogger(__name__)

class NotificationHandler(logging.StreamHandler):
    """This handler will catch all logs and emit a notification
       if a notification type is set in extra dictionary, in log record.

       Example usage is in external documentation.
    """
    loaded_notifications = False

    # This dictionary stores functions handling registered notifications
    # key - notification type, value - function handle
    notification_functions = {}

    @classmethod
    def send_notification(cls, user, notification_type,
            notification_message, notificaion_message_arguments):
        """This function will send a notification for a specified person.
           It will be done by sending a message to RabbitMQ.

           :param user: User, to whom the notification will be sent.

           :param notification_message: A message to show to notified user,
               which will be translated by frontend to his language
               and interpolated using notification_message_arguments.
               Remember to mark this message to translate, passing it as
               argument to _() function, so that the message string will be
               caught to translate.

           :param notification_message_arguments: A map which contains
               strings to interpolate notification_message, and special
               optional parameter "link" -- absolute link
               (starting with http://) to page related to
               the notification, where user can check the details.
        """
        pass

    @classmethod
    def register_notification(cls, notification_type, notification_function):
        """Register a specific notification handler function for
           specified type of notification, that will be executed
           each time the log with this notification type will be
           processed.
        """
        if notification_type in cls.notification_functions:
            logger.warning("Notification %s was registered twice",
                notification_type)
        cls.notification_functions[notification_type] = notification_function

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
            notification_type = getattr(record, 'notification')
            if notification_type in NotificationHandler.notification_functions:
                notification_function = NotificationHandler \
                    .notification_functions[notification_type]
                notification_function(record)
            else:
                logger.error("Internal error in notification module:"
                        " Tried to handle a non-exisitent notification \"%s\""
                        " Please check, if the notification is"
                        " registered correctly.", notification_type)
