from djcelery.loaders import DjangoLoader

from oioioi.filetracker.client import get_client


class OioioiLoader(DjangoLoader):
    def on_worker_init(self):
        super(OioioiLoader, self).on_worker_init()

        # This initializes sioworker's filetracker client as well.
        get_client()
