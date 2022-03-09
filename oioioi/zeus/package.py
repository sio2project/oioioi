import logging
import os

from django.core.validators import slug_re
from django.utils.translation import gettext as _
from six.moves import filter, map

from oioioi.sinolpack.package import (
    SinolPackage,
    SinolPackageBackend,
    SinolPackageCreator,
)
from oioioi.zeus.models import ZeusProblemData

logger = logging.getLogger(__name__)


class ZeusPackage(SinolPackage):
    controller_name = 'oioioi.zeus.controllers.ZeusProblemController'
    package_backend_name = 'oioioi.zeus.package.ZeusPackageBackend'

    def _find_main_dir(self):
        files = list(map(os.path.normcase, self.archive.filenames()))
        files = list(map(os.path.normpath, files))
        toplevel_folders = set(f.split(os.sep)[0] for f in files)
        toplevel_folders = list(filter(slug_re.match, toplevel_folders))

        folder = super(ZeusPackage, self)._find_main_dir()
        if not folder and len(toplevel_folders) > 0:
            folder = toplevel_folders[0]
        return folder

    def _save_zeus_data(self):
        problem_data, _created = ZeusProblemData.objects.get_or_create(
            problem=self.problem
        )
        problem_data.zeus_id = self.env['zeus_id']
        problem_data.zeus_problem_id = self.env['zeus_problem_id']
        problem_data.save()

    def _process_package(self):
        self._save_zeus_data()
        self._process_config_yml()
        self._detect_full_name()
        self._detect_library()
        self._extract_makefiles()
        self._process_statements()
        self._process_model_solutions()
        self._save_original_package()


class ZeusPackageCreator(SinolPackageCreator):
    def _pack_tests(self):
        pass


class ZeusPackageBackend(SinolPackageBackend):
    description = _("Zeus Package")
    package_class = ZeusPackage

    def identify(self, path, original_filename=None):
        # this PackageBackend should not be used other way than directly
        return False

    def pack(self, problem):
        return ZeusPackageCreator(problem).pack()
