from django.conf import settings
from oioioi.base.utils import get_object_by_dotted_name


def _get_backend():
    return get_object_by_dotted_name(settings.SIOWORKERS_BACKEND)()


def run_sioworkers_job(job, **kwargs):
    return _get_backend().run_job(job, **kwargs)


def run_sioworkers_jobs(dict_of_jobs, **kwargs):
    return _get_backend().run_jobs(dict_of_jobs, **kwargs)
