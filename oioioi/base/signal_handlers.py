from django.contrib.auth.signals import user_logged_in
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(user_logged_in)
def set_first_view_after_logging_flag(sender, user, request, **kwargs):
    request.session['first_view_after_logging'] = True


@receiver(connection_created)
def db_connection_callback(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.cursor().execute('PRAGMA legacy_alter_table = ON')
