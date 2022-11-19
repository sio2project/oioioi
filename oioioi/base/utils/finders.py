import shutil
from distutils import spawn


def find_executable_path(name):
    return shutil.which(name)
