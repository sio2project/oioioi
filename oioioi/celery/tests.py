from celery import Celery
from oioioi.base.tests import TestCase
from oioioi.celery.celery import enable_publisher_confirms

CONFIRMS = {"confirm_publish": True}


class TestEnablePublisherConfirms(TestCase):
    def _transport_options(self, broker_transport_options=None, **settings):
        app = Celery(set_as_current=False)
        app.conf.update(broker_transport_options=broker_transport_options, **settings)
        enable_publisher_confirms(app)
        return app.conf.broker_transport_options

    def test_amqp_url(self):
        for url in ["amqp://broker:5672//", "amqps://broker:5671//", "pyamqp://broker:5672//", "AMQPS://broker:5671//"]:
            self.assertEqual(self._transport_options(broker_url=url), CONFIRMS)

    def test_amqp_url_list(self):
        urls = ["amqp://n1:5672//", "amqp://n2:5672//"]
        self.assertEqual(self._transport_options(broker_url=urls), CONFIRMS)
        self.assertEqual(self._transport_options(broker_url=tuple(urls)), CONFIRMS)

    def test_amqp_semicolon_separated_urls(self):
        self.assertEqual(self._transport_options(broker_url="amqp://n1:5672//;amqp://n2:5672//"), CONFIRMS)

    def test_non_amqp_url(self):
        self.assertIsNone(self._transport_options(broker_url="sqla+sqlite:///celery.db"))
        self.assertIsNone(self._transport_options(broker_url=["sqla+sqlite:///celery.db"]))

    def test_no_url_defaults_to_amqp(self):
        for url in [None, ""]:
            self.assertEqual(self._transport_options(broker_url=url), CONFIRMS)

    def test_read_and_write_urls_must_both_be_amqp(self):
        self.assertIsNone(self._transport_options(broker_url="sqla+sqlite:///celery.db", broker_write_url="amqp://broker:5672//"))
        self.assertIsNone(self._transport_options(broker_url="amqp://broker:5672//", broker_write_url="sqla+sqlite:///celery.db"))
        self.assertEqual(self._transport_options(broker_read_url="amqp://n1:5672//", broker_write_url="amqp://n2:5672//"), CONFIRMS)

    def test_broker_transport_overrides_url_scheme(self):
        self.assertIsNone(self._transport_options(broker_url="amqp://broker:5672//", broker_transport="sqla"))

    def test_keeps_existing_transport_options(self):
        options = self._transport_options(broker_url=["amqp://n1:5672//"], broker_transport_options={"confirm_publish": False, "max_retries": 3})
        self.assertEqual(options, {"confirm_publish": False, "max_retries": 3})
