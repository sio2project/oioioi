import fcntl
import os.path

from django.conf import settings


FILELOCK_BASEDIR = settings.FILELOCK_BASEDIR


class FileLock(object):
    def __init__(self, filename):
        path = os.path.join(FILELOCK_BASEDIR, filename)
        try:
            os.makedirs(FILELOCK_BASEDIR, 0700)
        except OSError as e:
            if e.errno != os.errno.EEXIST or os.path.isfile(FILELOCK_BASEDIR):
                raise
        self.fd = os.open(path + '.lock', os.O_WRONLY | os.O_CREAT, 0600)

    def lock_shared(self):
        fcntl.flock(self.fd, fcntl.LOCK_SH)

    def lock_exclusive(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)

    def unlock(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)

    def __del__(self):
        self.unlock()
        os.close(self.fd)
