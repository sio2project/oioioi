import sys
import shutil
import distutils


def find_executable_path(name):
    if sys.version_info[0] >= 3:
        return shutil.which(name)
    else:
        return distutils.spawn.find_executable(name)
