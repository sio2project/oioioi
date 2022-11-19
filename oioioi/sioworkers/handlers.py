from oioioi.sioworkers.jobs import send_async_jobs

_STRIPPED_FIELDS = ['recipe', 'error_handlers']


def restore_job(saved_environ, resuming_environ):
    """Resuming env after getting it back from sioworkersd."""
    for field in _STRIPPED_FIELDS:
        if field in resuming_environ:
            raise RuntimeError(
                'Resuming environ contains stripped field {}.'.format(field)
            )
    saved_environ.update(resuming_environ)
    return saved_environ


def transfer_job(environ):
    """Removes fields from environ that aren't needed by sioworkersd and
    sends it. Environ is already saved in database.
    """
    for field in _STRIPPED_FIELDS:
        if field in environ:
            del environ[field]
    send_async_jobs(environ)
