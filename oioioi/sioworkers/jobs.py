from django.conf import settings
from django.utils.module_loading import import_string


def _get_backend():
    return import_string(settings.SIOWORKERS_BACKEND)()


# The url is added to job because worker needs to know which filetracker
# server it should access.
def run_sioworkers_job(job, **kwargs):
    if settings.FILETRACKER_URL:
        job["filetracker_url"] = settings.FILETRACKER_URL
    return _get_backend().run_job(job, **kwargs)


def run_sioworkers_jobs(dict_of_jobs, **kwargs):
    if settings.FILETRACKER_URL:
        for _, env in dict_of_jobs.items():
            env["filetracker_url"] = settings.FILETRACKER_URL
    return _get_backend().run_jobs(dict_of_jobs, **kwargs)


def send_async_jobs(dict_of_jobs, **kwargs):
    if settings.FILETRACKER_URL:
        for _, job in dict_of_jobs["workers_jobs"].items():
            job["filetracker_url"] = settings.FILETRACKER_URL
    return _get_backend().send_async_jobs(dict_of_jobs, **kwargs)
