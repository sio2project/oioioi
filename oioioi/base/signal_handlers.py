import django
from django.contrib.auth.signals import user_logged_in
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(user_logged_in)
def set_first_view_after_logging_flag(sender, user, request, **kwargs):
    request.session['first_view_after_logging'] = True


# Workaround for https://code.djangoproject.com/ticket/29182
# TODO: delete after upgrade to Django 2.1+
assert django.VERSION < (2, 1, 5)


@receiver(connection_created)
def db_connection_callback(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.cursor().execute('PRAGMA legacy_alter_table = ON')
