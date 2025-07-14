import json

# This is a workaround for SIO-915. We assume that other parts of OIOIOI code
# do not rely on particular directory being the current directory. Without
# this assumption, even a single call to LocalClient.build would break that
# code.
from threading import Lock
from xmlrpc.client import Server

import sio.workers.runner
from django.conf import settings
from django.db import transaction

from oioioi.evalmgr.tasks import delay_environ

_local_backend_lock = Lock()


class LocalBackend:
    """A simple sioworkers backend which executes the work in the calling
    process.

    Perfect for tests or a single-machine OIOIOI setup.
    """

    def run_job(self, job, **kwargs):
        with _local_backend_lock:
            return sio.workers.runner.run(job)

    def run_jobs(self, dict_of_jobs, **kwargs):
        results = {}
        for key, value in dict_of_jobs.items():
            results[key] = self.run_job(value, **kwargs)
        return results

    def send_async_jobs(self, env, **kwargs):
        res = self.run_jobs(env["workers_jobs"], **(env.get("workers_jobs.extra_args", dict())))
        env["workers_jobs.results"] = res
        del env["workers_jobs"]
        if "workers_jobs.extra_args" in env:
            del env["workers_jobs.extra_args"]
        with transaction.atomic():
            delay_environ(env)


class SioworkersdBackend:
    """A backend which collaborates with sioworkersd"""

    server = Server(settings.SIOWORKERSD_URL, allow_none=True)

    def run_job(self, job, **kwargs):
        env = {"workers_jobs": {"dummy_name": job}}
        env["workers_jobs.extra_args"] = kwargs
        env["oioioi_instance"] = settings.SITE_NAME
        env["contest_priority"] = settings.OIOIOI_INSTANCE_PRIORITY_BONUS + settings.NON_CONTEST_PRIORITY
        env["contest_weight"] = settings.OIOIOI_INSTANCE_WEIGHT_BONUS + settings.NON_CONTEST_WEIGHT
        ans = SioworkersdBackend.server.sync_run_group(json.dumps(env))
        if "error" in ans:
            raise RuntimeError("Error from workers:\n%s\nTB:\n%s" % (ans["error"]["message"], ans["error"]["traceback"]))
        return ans["workers_jobs.results"]["dummy_name"]

    def run_jobs(self, dict_of_jobs, **kwargs):
        env = {"workers_jobs": dict_of_jobs, "workers_jobs.extra_args": kwargs}
        env["oioioi_instance"] = settings.SITE_NAME
        env["contest_priority"] = settings.OIOIOI_INSTANCE_PRIORITY_BONUS + settings.NON_CONTEST_PRIORITY
        env["contest_weight"] = settings.OIOIOI_INSTANCE_WEIGHT_BONUS + settings.NON_CONTEST_WEIGHT
        ans = SioworkersdBackend.server.sync_run_group(json.dumps(env))
        if "error" in ans:
            raise RuntimeError("Error from workers:\n%s\nTB:\n%s" % (ans["error"]["message"], ans["error"]["traceback"]))
        return ans["workers_jobs.results"]

    def send_async_jobs(self, env, **kwargs):
        url = settings.SIOWORKERS_LISTEN_URL
        if url is None:
            url = "http://" + settings.SIOWORKERS_LISTEN_ADDR + ":" + str(settings.SIOWORKERS_LISTEN_PORT)
        env["return_url"] = url
        SioworkersdBackend.server.run_group(json.dumps(env))
