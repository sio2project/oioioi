import xmlrpc.client

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


class UnavailableServer:
    def get_workers(self):
        raise ConnectionRefusedError


class FaultingServer(TestServer):
    """Running sioworkersd that refuses to forget Komp4."""

    def __init__(self):
        self.forgotten = []

    def forget_worker(self, name):
        if name == "Komp4":
            raise xmlrpc.client.Fault(1, "Unknown worker Komp4")
        self.forgotten.append(name)


class UnavailableOnDeleteServer(TestServer):
    def forget_worker(self, name):
        raise ConnectionRefusedError


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

    def test_workers_page_reports_unavailable_service(self):
        views.server = UnavailableServer()
        self.assertTrue(self.client.login(username="test_admin"))

        response = self.client.get(reverse("show_workers"))

        self.assertContains(response, "The workers service is unavailable")
        self.assertNotContains(response, "worker_load_plot")

    def test_load_json_reports_unavailable_service(self):
        views.server = UnavailableServer()
        self.assertTrue(self.client.login(username="test_admin"))

        response = self.client.get(reverse("get_load_json"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "The workers service is unavailable."})

    def test_delete_fault_is_reported_and_list_kept(self):
        server = FaultingServer()
        views.server = server
        self.assertTrue(self.client.login(username="test_admin"))

        response = self.client.post(
            reverse("show_workers"),
            {"confirm": "1", "work-Komp4": "on", "work-Komp8": "on"},
        )

        self.assertEqual(server.forgotten, ["Komp8"])
        self.assertContains(response, "Could not delete some workers")
        self.assertContains(response, "Unknown worker Komp4")
        self.assertNotContains(response, "Successfully deleted selected workers")
        self.assertNotContains(response, "The workers service is unavailable")
        self.assertContains(response, "worker_load_plot")

    def test_delete_unavailable_keeps_list(self):
        views.server = UnavailableOnDeleteServer()
        self.assertTrue(self.client.login(username="test_admin"))

        response = self.client.post(reverse("show_workers"), {"confirm": "1", "work-Komp4": "on"})

        self.assertContains(response, "The workers service is unavailable")
        self.assertNotContains(response, "Successfully deleted selected workers")
        self.assertContains(response, "Komp8")
