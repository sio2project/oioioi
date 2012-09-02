from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
import json
import time

class TestClock(TestCase):
    def test_clock(self):
        client = Client()
        response = client.get(reverse('oioioi.clock.views.get_time_view'))
        response = json.loads(response.content)
        response_time = response['time']
        now = time.time()
        self.assertLessEqual(response_time, now)
        self.assertGreater(response_time, now - 10)
