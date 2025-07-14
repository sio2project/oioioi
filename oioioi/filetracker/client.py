from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.test.signals import setting_changed
from django.utils.module_loading import import_string

from filetracker.client import Client as FiletrackerClient
from oioioi.base.utils import memoized, reset_memoized


@memoized
def get_client():
    """Constructs a Filetracker client.

    Needs a ``FILETRACKER_CLIENT_FACTORY`` entry in ``settings.py``, which
    should contain a :term:`dotted name` of a function which returns a
    :class:`filetracker.client.Client` instance. A good candidate is
    :func:`~oioioi.filetracker.client.remote_storage_factory`.

    The constructed client is cached.
    """
    factory = settings.FILETRACKER_CLIENT_FACTORY
    if isinstance(factory, str):
        factory = import_string(factory)
    if not callable(factory):
        raise ImproperlyConfigured("The FILETRACKER_CLIENT_FACTORY setting refers to non-callable: %r" % (factory,))
    client = factory()
    if not isinstance(client, FiletrackerClient):
        raise ImproperlyConfigured("The factory pointed by FILETRACKER_CLIENT_FACTORY returned non-FiletrackerClient: %r" % (client,))

    # Needed for oioioi.sioworkers.backends.LocalBackend so that both Django
    # and sioworkers use the same Filetracker client
    import sio.workers.ft

    sio.workers.ft.set_instance(client)

    return client


@receiver(setting_changed)
def _on_setting_changed(sender, setting, **kwargs):
    if setting == "FILETRACKER_CLIENT_FACTORY":
        reset_memoized(get_client)


def remote_storage_factory():
    """A filetracker factory which creates a client that uses the
    remote server at ``settings.FILETRACKER_URL`` and a folder
    ``settings.FILETRACKER_CACHE_ROOT`` as a cache directory.
    """
    return FiletrackerClient(remote_url=settings.FILETRACKER_URL, cache_dir=settings.FILETRACKER_CACHE_ROOT)
