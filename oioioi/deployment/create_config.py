from oioioi.base.utils.execute import execute
from optparse import OptionParser
import os
import os.path
import sys
import uuid
import pwd
import grp
import shutil

basedir = os.path.abspath(os.path.dirname(__file__))

def error(message):
    print >>sys.stderr, "error:", message
    sys.exit(1)

def get_timezone():
    try:
        return open('/etc/timezone').read().strip()
    except IOError:
        return 'GMT'

def find_site_packages():
    from distutils.sysconfig import get_python_lib
    return get_python_lib()

def generate_from_template(dir, filename, context):
    dest = os.path.join(dir, filename)
    template = open(os.path.join(basedir, filename + '.template')).read()
    for key, value in context.iteritems():
        template = template.replace(key, value)
    open(dest, 'w').write(template)

def generate_all(dir):
    generate_from_template(dir, 'settings.py', {
            '__DIR__': dir,
            '__SECRET__': str(uuid.uuid4()),
            '__TIMEZONE__': get_timezone(),
        })

    settings = {}
    settings_py = os.path.join(dir, 'settings.py')
    execfile(settings_py, globals(), settings)
    media_root = settings['MEDIA_ROOT']
    os.mkdir(media_root)

    static_root = settings['STATIC_ROOT']
    os.mkdir(static_root)

    os.mkdir(os.path.join(dir, 'logs'))
    os.mkdir(os.path.join(dir, 'pidfiles'))

    virtual_env = os.environ.get('VIRTUAL_ENV', ''),
    site_packages = find_site_packages()
    user = pwd.getpwuid(os.getuid())[0],
    group = grp.getgrgid(os.getgid())[0],

    manage_py = os.path.join(dir, 'manage.py')
    generate_from_template(dir, 'manage.py', {
            '__DIR__': dir,
            '__PYTHON_EXECUTABLE__': sys.executable,
            '__VIRTUAL_ENV__': virtual_env,
            '__SITE_PACKAGES__': site_packages,
        })
    os.chmod(manage_py, 0755)

    generate_from_template(dir, 'supervisord.conf', {
            '__USER__': user,
        })

    generate_from_template(dir, 'wsgi.py', {
            '__DIR__': dir,
            '__VIRTUAL_ENV__': virtual_env,
            '__SITE_PACKAGES__': site_packages,
        })

    generate_from_template(dir, 'apache-site.conf', {
            '__DIR__': dir,
            '__STATIC_URL__': settings['STATIC_URL'],
            '__STATIC_ROOT__': settings['STATIC_ROOT'],
            '__USER__': user,
            '__GROUP__': group,
        })

    # Having DJANGO_SETTINGS_MODULE here would probably cause collectstatic to
    # run with wrong settings.
    os.environ.pop('DJANGO_SETTINGS_MODULE', None)
    execute([sys.executable, manage_py, 'collectstatic', '--noinput'],
            capture_output=False)

def main():
    usage = "usage: %prog [options] dir"
    parser = OptionParser(usage=usage)
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("expected a single argument: deployment folder to create")
    dir = os.path.abspath(args[0])

    if os.path.exists(dir):
        error("%s already exists; please specify another location" % (dir,))

    os.makedirs(dir)

    try:
        generate_all(dir)
    except BaseException, e:
        shutil.rmtree(dir)
        raise

    print >>sys.stderr
    print >>sys.stderr, "Initial configuration created. Please adjust "
    print >>sys.stderr, "settings.py to your taste."
