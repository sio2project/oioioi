from types import SimpleNamespace

from oioioi.base.tests import TestCase
from oioioi.celery.celery import enable_publisher_confirms


class TestEnablePublisherConfirms(TestCase):
    def _transport_options(self, broker_url, broker_transport_options=None):
        conf = SimpleNamespace(broker_url=broker_url, broker_transport_options=broker_transport_options)
        enable_publisher_confirms(SimpleNamespace(conf=conf))
        return conf.broker_transport_options

    def test_amqp_url(self):
        for url in ["amqp://broker:5672//", "amqps://broker:5671//", "pyamqp://broker:5672//"]:
            self.assertEqual(self._transport_options(url), {"confirm_publish": True})

    def test_amqp_url_list(self):
        urls = ["amqp://n1:5672//", "amqp://n2:5672//"]
        self.assertEqual(self._transport_options(urls), {"confirm_publish": True})
        self.assertEqual(self._transport_options(tuple(urls)), {"confirm_publish": True})

    def test_amqp_semicolon_separated_urls(self):
        self.assertEqual(self._transport_options("amqp://n1:5672//;amqp://n2:5672//"), {"confirm_publish": True})

    def test_non_amqp_url(self):
        self.assertIsNone(self._transport_options("sqla+sqlite:///celery.db"))
        self.assertIsNone(self._transport_options(["sqla+sqlite:///celery.db"]))

    def test_no_url(self):
        for url in [None, "", [], ()]:
            self.assertIsNone(self._transport_options(url))

    def test_keeps_existing_transport_options(self):
        options = self._transport_options(["amqp://n1:5672//"], {"confirm_publish": False, "max_retries": 3})
        self.assertEqual(options, {"confirm_publish": False, "max_retries": 3})
