import oioioi

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

import os
import tarfile
import tempfile
import shutil
import subprocess


class Command(BaseCommand):

    def handle(self, *args, **options):
        tables = connection.introspection.table_names()
        if 'south_migrationhistory' not in tables:
            self.stderr.write("The database used with this project was never "
                              "used with previous versions of Django.")
            return

        query = "SELECT * from south_migrationhistory " \
                "WHERE migration = '0002_final_south_migration'"
        with connection.cursor() as cursor:
            cursor.execute(query)
            if cursor.rowcount != 0:
                self.stderr.write("Already upgraded.")
                return

        deployment_dir = os.getcwd()
        upgrade_dir = tempfile.mkdtemp()
        try:
            package_dir = os.path.dirname(os.path.dirname(oioioi.__file__))
            package_name = os.path.join(package_dir, 'upgrade_package.tar')
            with tarfile.open(package_name) as package:
                package.extractall(path=upgrade_dir)

            unpacked_dir = os.path.join(upgrade_dir, 'upgrade_package')
            migrate_south_settings_path = \
                os.path.join(unpacked_dir, 'migrate_south_settings.py')
            with open(migrate_south_settings_path, 'a') as file:
                file.write('DATABASES = ' + repr(settings.DATABASES) + '\n')

            # Apply all South migrations.
            venv_dir = os.path.join(upgrade_dir, 'venv')
            subprocess.check_call(['virtualenv', venv_dir])
            migrate_south_script = os.path.join(unpacked_dir,
                                                'migrate_south.sh')
            env = {'PYTHONPATH': os.path.join(unpacked_dir, 'oioioi')}
            subprocess.call([migrate_south_script], env=env, cwd=unpacked_dir)

            shutil.copy(os.path.join(unpacked_dir, 'all_apps_settings.py'),
                        deployment_dir)
        finally:
            shutil.rmtree(upgrade_dir)

        # Apply all Django 1.7 migrations.
        script_contents = """
for app in balloons complaints contestexcl contestlogo contests
do
    ./manage.py migrate $app 0002 --fake --settings={0}
done
./manage.py migrate --settings={0}
        """.format('all_apps_settings')

        with tempfile.NamedTemporaryFile(dir=deployment_dir) as script_file:
            script_file.write(script_contents)
            script_file.flush()
            subprocess.call(['/bin/bash', script_file.name])
        os.remove(os.path.join(os.getcwd(), 'all_apps_settings.py'))
        os.remove(os.path.join(os.getcwd(), 'all_apps_settings.pyc'))
