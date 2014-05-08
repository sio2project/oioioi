import logging
import shutil
import tempfile
import os

from django.core.validators import slug_re
from django.utils.translation import ugettext as _

from oioioi.problems.models import Problem
from oioioi.problems.package import ProblemPackageBackend, ProblemPackageError
from oioioi.sinolpack.package import SinolPackageCreator, SinolPackage


logger = logging.getLogger(__name__)


class ZeusPackage(SinolPackage):

    def _find_main_folder(self):
        files = map(os.path.normcase, self.archive.filenames())
        files = map(os.path.normpath, files)
        toplevel_folders = set(f.split(os.sep)[0] for f in files)
        toplevel_folders = filter(slug_re.match, toplevel_folders)

        folder = super(ZeusPackage, self)._find_main_folder()
        if not folder and len(toplevel_folders) > 0:
            folder = toplevel_folders[0]
        return folder

    def unpack(self, existing_problem=None):
        self.short_name = self._find_main_folder()

        if existing_problem:
            self.problem = existing_problem
            if existing_problem.short_name != self.short_name:
                raise ProblemPackageError(
                    _("Tried to replace problem "
                      "'%(oldname)s' with '%(newname)s'. For safety, changing "
                      "problem short name is not possible.") %
                    dict(oldname=existing_problem.short_name,
                         newname=self.short_name)
                )
        else:
            self.problem = Problem(
                name=self.short_name,
                short_name=self.short_name,
                controller_name='oioioi.zeus.controllers.'
                                'ZeusProblemController')

        self.problem.package_backend_name = \
            'oioioi.zeus.package.ZeusPackageBackend'
        self.problem.save()

        tmpdir = tempfile.mkdtemp()
        logger.info('%s: tmpdir is %s', self.filename, tmpdir)
        try:
            self.archive.extract(to_path=tmpdir)
            self.rootdir = os.path.join(tmpdir, self.short_name)
            self._process_config_yml()
            self._detect_full_name()
            self._detect_library()
            self._extract_makefiles()
            self._process_statements()
            self._process_model_solutions()
            self._save_original_package()
            return self.problem
        finally:
            shutil.rmtree(tmpdir)


class ZeusPackageCreator(SinolPackageCreator):
    def _pack_tests(self):
        pass


class ZeusPackageBackend(ProblemPackageBackend):
    description = _("Zeus Package")

    def identify(self, path, original_filename=None):
        # this PackageBackend should not be used other way than directly
        return False

    def unpack(self, path, original_filename=None, existing_problem=None):
        return ZeusPackage(path, original_filename) \
                .unpack(existing_problem)

    def pack(self, problem):
        return ZeusPackageCreator(problem).pack()
