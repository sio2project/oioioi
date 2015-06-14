import sio.workers.runner
import sio.celery.job
import oioioi


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

    def run_job(self, job, **kwargs):
        with _local_backend_lock:
            return sio.workers.runner.run(job)

    def run_jobs(self, dict_of_jobs, **kwargs):
        results = {}
        for key, value in dict_of_jobs.iteritems():
            results[key] = self.run_job(value, **kwargs)
        return results

    def send_async_jobs(self, env, **kwargs):
        res = self.run_jobs(env['workers_jobs'],
            **(env.get('workers_jobs.extra_args', dict())))
        env['workers_job.results'] = res
        del env["workers_jobs"]
        if 'workers_jobs.extra_args' in env:
            del env['workers_jobs.extra_args']
        oioioi.evalmgr.evalmgr_job.delay(env)


class CeleryBackend(object):
    """A backend which uses Celery for sioworkers jobs."""

    def _delayed_job(self, job, **kwargs):
        return sio.celery.job.sioworkers_job.apply_async(args=[job], **kwargs)

    def run_job(self, job, **kwargs):
        return self._delayed_job(job, **kwargs).get()

    def run_jobs(self, dict_of_jobs, **kwargs):
        async_jobs = dict()
        for key, env in dict_of_jobs.iteritems():
            async_jobs[key] = sio.celery.job.sioworkers_job.apply_async(
                args=[env], **kwargs)
        results = dict()
        for key, async_job in async_jobs.iteritems():
            results[key] = async_job.get()
        return results

    def send_async_jobs(self, env, **kwargs):
        res = self.run_jobs(env['workers_jobs'],
            **(env.get('workers_jobs.extra_args', dict())))
        env['workers_job.results'] = res
        del env["workers_jobs"]
        if 'workers_jobs.extra_args' in env:
            del env['workers_jobs.extra_args']
        oioioi.evalmgr.evalmgr_job.delay(env)
