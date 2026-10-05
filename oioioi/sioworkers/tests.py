from django.test import TestCase

from oioioi.sioworkers.jobs import run_sioworkers_job, run_sioworkers_jobs


class TestSioworkersBindings(TestCase):
    def test_sioworkers_bindings(self):
        env = run_sioworkers_job({"job_type": "ping", "ping": "e1"})
        self.assertEqual(env.get("pong"), "e1")
        envs = run_sioworkers_jobs(
            {
                "key1": {"job_type": "ping", "ping": "e1"},
                "key2": {"job_type": "ping", "ping": "e2"},
            }
        )
        self.assertEqual(envs["key1"].get("pong"), "e1")
        self.assertEqual(envs["key2"].get("pong"), "e2")
        self.assertEqual(len(envs), 2)
