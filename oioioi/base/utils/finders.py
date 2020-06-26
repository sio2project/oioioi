import shutil
from distutils import spawn

import six


def find_executable_path(name):
    if six.PY3:
        return shutil.which(name)
    else:
        return spawn.find_executable(name)
