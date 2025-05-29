import json
import logging
import threading
import time
import uuid

import urllib.parse
from django.conf import settings
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from pika.exceptions import AMQPChannelError, AMQPConnectionError

from oioioi.base.utils.loaders import load_modules

logger = logging.getLogger(__name__)
thread_data = threading.local()


class NotificationHandler(logging.StreamHandler):
    """This handler catches all logs and emits a notification
    if a notification type is set in the extra dictionary,
    in the log record.
    """

    # Example usage may be found in external documentation.
    # Link: https://sio2project.github.io/oioioi/sections/notifications.html

    loaded_notifications = False

    # This dictionary stores functions handling registered notifications
    # key - notification type, value - function handle
    notification_functions = {}

    notification_queue_prefix = '_notifs_'
    last_connection_check = 0
    conn_try_interval = 30

    @classmethod
    def _check_connection(cls):
        if (
            not getattr(thread_data, 'rabbitmq_connected', False)
            and 'oioioi.notifications' in settings.INSTALLED_APPS
            and NotificationHandler.last_connection_check
            < time.time() - NotificationHandler.conn_try_interval
        ):
            try:
                o = urllib.parse.urlparse(settings.NOTIFICATIONS_RABBITMQ_URL)
                kwargs = {}
                if o.hostname:
                    kwargs['host'] = o.hostname
                if o.port:
                    kwargs['port'] = o.port
                if o.path:
                    kwargs['virtual_host'] = o.path
                if o.username and o.password:
                    kwargs['credentials'] = PlainCredentials(o.username, o.password)
                kwargs.update(settings.NOTIFICATIONS_RABBITMQ_EXTRA_PARAMS)
                kwargs['heartbeat'] = 8
                parameters = ConnectionParameters(**kwargs)
                thread_data.conn = BlockingConnection(parameters)

                thread_data.rabbitmq_connected = True
            # pylint: disable=broad-except
            except Exception:
                NotificationHandler.last_connection_check = time.time()
                logger.info("Notifications: Can't connect to RabbitMQ", exc_info=True)

    @classmethod
    def _send_notification_message(cls, user, message, repeated=False):
        if not hasattr(thread_data, 'conn') or not getattr(
            thread_data, 'rabbitmq_connected', False
        ):
            return

        try:
            queue_name = NotificationHandler.notification_queue_prefix + str(user.pk)
            channel = thread_data.conn.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_publish(
                exchange='', routing_key=queue_name, body=json.dumps(message)
            )
        except (AMQPChannelError, AMQPConnectionError):
            logger.info("Notifications: Connection with RabbitMQ broken", exc_info=True)
            thread_data.rabbitmq_connected = False

            # Make a second try
            if not repeated:
                NotificationHandler._check_connection()
                NotificationHandler._send_notification_message(
                    user, message, repeated=True
                )

    @classmethod
    def send_notification(
        cls,
        user,
        notification_type,
        notification_message,
        notification_message_arguments,
    ):
        """This function sends a notification to the specified user
        by sending a message to RabbitMQ.

        :param user: User, to whom the notification will be sent.

        :param notification_type: A string which describes the notification
            type.

        :param notification_message: A message to show to the notified user,
            which will be translated by frontend to their language
            and interpolated using notification_message_arguments.
            Remember to mark this message to translate, passing it as
            argument to _() function, so that the message string will be
            caught to translate.

        :param notification_message_arguments: A map which contains
            strings to interpolate notification_message and special
            optional parameters:
                * "address" -- an absolute link
                    (starting with http://) to a page related to
                    the notification, where the user can check the details.
                * "details" -- a short information
                    for the user about the event.
                * "popup" -- if set the related dropdown will be opened in ui.
        """

        NotificationHandler._check_connection()

        message = {}

        # Id of a message is an unique uuid4.
        message['id'] = str(uuid.uuid4())

        message['date'] = round(time.time() * 1000)
        message['message'] = notification_message
        message['type'] = notification_type

        if 'details' in notification_message_arguments:
            message['details'] = notification_message_arguments['details']

        if 'address' in notification_message_arguments:
            message['address'] = notification_message_arguments['address']

        if 'popup' in notification_message_arguments:
            message['popup'] = notification_message_arguments['popup']

        message['arguments'] = notification_message_arguments

        NotificationHandler._send_notification_message(user, message)

    @classmethod
    def register_notification(cls, notification_type, notification_function):
        """Register a specific notification handler function for the
        specified type of notification, that will be executed
        each time a log with this notification type is processed.
        """
        if notification_type in cls.notification_functions:
            logger.warning("Notification %s was registered twice", notification_type)
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

        if (
            not NotificationHandler.loaded_notifications
            and 'oioioi.notifications' in settings.INSTALLED_APPS
        ):
            load_modules('notifications')
            NotificationHandler.loaded_notifications = True

        if hasattr(record, 'notification'):
            notification_type = getattr(record, 'notification')
            if notification_type in NotificationHandler.notification_functions:
                notification_function = NotificationHandler.notification_functions[
                    notification_type
                ]
                notification_function(record)
            else:
                logger.error(
                    "Internal error in notification module:"
                    " Tried to handle a non-exisitent notification \"%s\""
                    " Please check, if the notification is"
                    " registered correctly.",
                    notification_type,
                )
