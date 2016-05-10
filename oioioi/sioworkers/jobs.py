from django.conf import settings
from oioioi.base.utils import get_object_by_dotted_name


def _get_backend():
    return get_object_by_dotted_name(settings.SIOWORKERS_BACKEND)()


# The url is added to job because worker needs to know which filetracker
# server it should access.
def run_sioworkers_job(job, **kwargs):
    job['filetracker_url'] = settings.FILETRACKER_URL
    return _get_backend().run_job(job, **kwargs)


def run_sioworkers_jobs(dict_of_jobs, **kwargs):
    for _, env in dict_of_jobs.iteritems():
        env['filetracker_url'] = settings.FILETRACKER_URL
    return _get_backend().run_jobs(dict_of_jobs, **kwargs)


def send_async_jobs(dict_of_jobs, **kwargs):
    for _, job in dict_of_jobs['workers_jobs'].iteritems():
        job['filetracker_url'] = settings.FILETRACKER_URL
    return _get_backend().send_async_jobs(dict_of_jobs, **kwargs)
