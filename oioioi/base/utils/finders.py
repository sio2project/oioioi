import shutil


def find_executable_path(name):
    return shutil.which(name)
