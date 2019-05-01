from __future__ import print_function

import os
import os.path
import pwd
import shutil
import sys
import uuid
from argparse import ArgumentParser

import six

from oioioi.base.utils.execute import execute
from oioioi.default_settings import INSTALLATION_CONFIG_VERSION

basedir = os.path.abspath(os.path.dirname(__file__))


def error(message):
    print("error:", message, file=sys.stderr)
    sys.exit(1)


def get_timezone():
    ret = ''
    try:
        if os.path.isfile('/etc/timezone'):
            ret = open('/etc/timezone').read().strip()
        elif os.path.isfile('/etc/sysconfig/clock'):
            file = open('/etc/sysconfig/clock')
            for line in file:
                if 'ZONE' in line:
                    ret = ''.join(line.split())[6:-1]
        elif os.path.isfile('/etc/sysconfig/timezone'):
            file = open('/etc/sysconfig/timezone')
            for line in file:
                if 'TIMEZONE' in line:
                    ret = ''.join(line.split())[10:-1]
    except IOError:
        ret = 'GMT'
    if ret != '':
        return ret
    else:
        return 'GMT'


def generate_from_template(dir, filename, context, mode=None):
    dest = os.path.join(dir, filename)
    template = open(os.path.join(basedir, filename + '.template')).read()
    for key, value in six.iteritems(context):
        template = template.replace(key, value)
    open(dest, 'w').write(template)
    if mode is not None:
        os.chmod(dest, mode)


def generate_all(dir, verbose):
    generate_from_template(dir, 'settings.py', {
            '__CONFIG_VERSION__': str(INSTALLATION_CONFIG_VERSION),
            '__DIR__': dir,
            '__SECRET__': str(uuid.uuid4()),
            '__TIMEZONE__': get_timezone(),
        })

    settings = {}
    settings_py = os.path.join(dir, 'settings.py')
    six.exec_(compile(open(settings_py).read(), settings_py, 'exec'), globals(),
            settings)
    media_root = settings['MEDIA_ROOT']
    os.mkdir(media_root)

    static_root = settings['STATIC_ROOT']
    os.mkdir(static_root)

    os.mkdir(os.path.join(dir, 'logs'))
    os.mkdir(os.path.join(dir, 'pidfiles'))

    virtual_env = os.environ.get('VIRTUAL_ENV', '')
    user = pwd.getpwuid(os.getuid())[0]

    manage_py = os.path.join(dir, 'manage.py')
    generate_from_template(dir, 'manage.py', {
            '__DIR__': dir,
            '__PYTHON_EXECUTABLE__': sys.executable,
            '__VIRTUAL_ENV__': virtual_env,
        }, mode=0o755)

    generate_from_template(dir, 'supervisord.conf', {
            '__USER__': user,
        })

    generate_from_template(dir, 'wsgi.py', {
            '__DIR__': dir,
            '__VIRTUAL_ENV__': virtual_env,
        })

    generate_from_template(dir, 'start_supervisor.sh', {
            '__DIR__': dir,
            '__VIRTUAL_ENV__': virtual_env,
        }, mode=0o755)

    generate_from_template(dir, 'apache-site.conf', {
            '__DIR__': dir,
            '__STATIC_URL__': settings['STATIC_URL'],
            '__STATIC_ROOT__': settings['STATIC_ROOT'],
        })

    generate_from_template(dir, 'nginx-site.conf', {
            '__DIR__': dir,
            '__STATIC_URL__': settings['STATIC_URL'],
            '__STATIC_ROOT__': settings['STATIC_ROOT'],
        })

    # Having DJANGO_SETTINGS_MODULE here would probably cause collectstatic to
    # run with wrong settings.
    os.environ.pop('DJANGO_SETTINGS_MODULE', None)
    # Let's silence collectstatic a bit - a ton of (normally) useless logs
    # happen from it
    print('Collecting static files...', file=sys.stderr)
    cmd = [sys.executable, manage_py, 'collectstatic', '--noinput']
    if not verbose:
        cmd += ['-v', '0']
    execute(cmd,
            capture_output=False)


def main():
    usage = "%(prog)s [options] dir"
    parser = ArgumentParser(usage=usage)
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose')
    parser.add_argument("dir", help="deployment folder to create")
    args = parser.parse_args()

    absolute_dir = os.path.abspath(args.dir)

    if os.path.exists(absolute_dir):
        error("%s already exists; please specify another location" %
              (absolute_dir,))

    os.makedirs(absolute_dir)

    try:
        generate_all(absolute_dir, args.verbose)
    except BaseException:
        shutil.rmtree(absolute_dir)
        raise

    print(file=sys.stderr)
    print("Initial configuration created. Please adjust ", file=sys.stderr)
    print("settings.py to your taste.", file=sys.stderr)
