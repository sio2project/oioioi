from django.conf import settings
from django.contrib.staticfiles import finders
from oioioi.base.utils.execute import execute
import os.path
import shutil
import re
import sys
import tempfile

def find_staticfiles_path(fs_path):
    prefix, path = fs_path, ''
    longest_good = None
    while prefix != os.sep:
        prefix, new_component = os.path.split(prefix)
        path = os.path.join(new_component, path)
        if finders.find(path):
            longest_good = path
    if not longest_good:
        raise RuntimeError("File '%s' cannot be find in any of the "
                "static directories" % (fs_path,))
    return longest_good

LESS_IMPORT_RE = re.compile(r'^@import\s*[\'"]([^\'"]*)', re.I|re.M)

def collect_sources(tmp_dir, staticfiles_path):
    print >>sys.stderr, "Processing", staticfiles_path
    staticfiles_dir = os.path.dirname(staticfiles_path)
    dst_path = os.path.join(tmp_dir, staticfiles_path)
    dst_dir = os.path.dirname(dst_path)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    src_path = finders.find(staticfiles_path)
    shutil.copyfile(src_path, dst_path)

    content = open(dst_path, 'r').read()
    for match in re.finditer(content):
        url = match.group(1)
        if '://' in url:
            continue
        if os.path.isabs(url):
            continue
        collect_sources(tmp_dir, os.path.normpath(os.path.join(staticfiles_dir,
            url)))

def main():
    infile = os.path.realpath(os.path.abspath(sys.argv[1]))
    staticfiles_root = os.path.realpath(os.path.abspath(settings.STATIC_ROOT))
    staticfiles_root = staticfiles_root.rstrip(os.sep) + os.sep
    if infile.startswith(staticfiles_root):
        execute(['lessc'] + sys.argv[1:], capture_output=False)
        return

    tmpdir = tempfile.mkdtemp()
    try:
        os.chdir(tmpdir)
        staticfiles_path = find_staticfiles_path(infile)
        collect_sources(tmpdir, staticfiles_path)
        execute(['lessc', staticfiles_path] + sys.argv[2:],
                capture_output=False)
    finally:
        shutil.rmtree(tmpdir)
