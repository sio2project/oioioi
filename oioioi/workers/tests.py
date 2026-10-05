from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.workers import views


class TestServer:
    def get_workers(self):
        return [
            {
                "name": "Komp4",
                "info": {"concurrency": 2, "can_run_cpu_exec": True},
                "tasks": [{}],
                "is_running_cpu_exec": False,
            },
            {
                "name": "Komp8",
                "info": {"concurrency": 4, "can_run_cpu_exec": True},
                "tasks": [],
                "is_running_cpu_exec": True,
            },
        ]


class TestWorkersInfo(TestCase):
    fixtures = ["test_users"]

    def setUp(self):
        # monkeypatch test server instead of XMLRPC
        views.server = TestServer()

    def test_admin_can_see(self):
        self.assertTrue(self.client.login(username="test_admin"))
        url = reverse("show_workers")
        response = self.client.get(url)
        self.assertContains(response, "Komp4")

    def test_mundane_user_cant_see(self):
        self.assertTrue(self.client.login(username="test_user"))
        url = reverse("show_workers")
        response = self.client.get(url)
        self.assertNotContains(response, "Komp4", status_code=403)

    def test_load_json(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(reverse("get_load_json"))
        self.assertEqual(
            response.json(),
            {"capacity": 6, "load": 5, "cpu_exec_load": 4},
        )
