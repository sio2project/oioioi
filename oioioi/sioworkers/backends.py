import sio.workers.runner
import sio.celery.job

# This is a workaround for SIO-915. We assume that other parts of OIOIOI code
# do not rely on particular directory being the current directory. Without
# this assumption, even a single call to LocalClient.build would break that
# code.
from threading import Lock
_local_backend_lock = Lock()

class LocalBackend(object):
    """A simple sioworkers backend which executes the work in the calling
       process.

       Perfect for tests or a single-machine OIOIOI setup.
    """

    def run_job(self, job):
        with _local_backend_lock:
            return sio.workers.runner.run(job)

    def run_jobs(self, dict_of_jobs):
        results = {}
        for key, value in dict_of_jobs.iteritems():
            results[key] = self.run_job(value)
        return results

class CeleryBackend(object):
    """A backend which uses Celery for sioworkers jobs."""

    def _delayed_job(self, job):
        return sio.celery.job.sioworkers_job.delay(job)

    def run_job(self, job):
        return self._delayed_job(job).get()

    def run_jobs(self, dict_of_jobs):
        async_jobs = dict()
        for key, env in dict_of_jobs.iteritems():
            async_jobs[key] = sio.celery.job.sioworkers_job.delay(env)
        results = dict()
        for key, async_job in async_jobs.iteritems():
            results[key] = async_job.get()
        return results
