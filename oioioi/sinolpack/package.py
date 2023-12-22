import functools
import glob
import io
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile

import chardet
import six

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import slug_re
from django.utils.translation import gettext as _
from oioioi.base.utils import generate_key, naturalsort_key
from oioioi.base.utils.archive import Archive
from oioioi.base.utils.execute import ExecuteError, execute
from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import (
    django_to_filetracker_path,
    filetracker_to_django_file,
    stream_file,
)
from oioioi.problems.models import (
    Problem,
    ProblemAttachment,
    ProblemName,
    ProblemPackage,
    ProblemSite,
    ProblemStatement,
)
from oioioi.problems.package import (
    PackageProcessingError,
    ProblemPackageBackend,
    ProblemPackageError,
)
from oioioi.programs.models import (
    LanguageOverrideForTest,
    LibraryProblemData,
    ModelSolution,
    OutputChecker,
    Test,
)
from oioioi.sinolpack.models import ExtraConfig, ExtraFile, OriginalPackage
from oioioi.sinolpack.utils import add_extra_files
from oioioi.sioworkers.jobs import run_sioworkers_job, run_sioworkers_jobs

logger = logging.getLogger(__name__)

DEFAULT_TIME_LIMIT = 10000
DEFAULT_MEMORY_LIMIT = 66000
TASK_PRIORITY = 500
C_EXTRA_ARGS = ['-Wall', '-Wno-unused-result', '-Werror']
PAS_EXTRA_ARGS = ['-Ci', '-Cr', '-Co', '-gl']


def _stringify_keys(dictionary):
    return dict((str(k), v) for k, v in dictionary.items())


def _determine_encoding(title, file):
    r = re.search(br'\\documentclass\[(.+)\]{sinol}', file)
    encoding = 'latin2'

    if r is not None and b'utf8' in r.group(1):
        encoding = 'utf8'
    else:
        result = chardet.detect(title)
        if result['encoding'] == 'utf-8':
            encoding = 'utf-8'

    return encoding


def _decode(title, file):
    encoding = _determine_encoding(title, file)
    return title.decode(encoding)


def _make_filename_in_job_dir(env, base_name):
    env['unpack_dir'] = '/unpack/%s' % (env['package_id'])
    if 'job_id' not in env:
        env['job_id'] = 'local'
    return '%s/%s-%s' % (env['unpack_dir'], env['job_id'], base_name)


def _remove_from_zip(zipfname, *filenames):
    """Removes files from zip file by creating new zip file with all
    the files except the files to remove. Then the old file is removed.
    It has to be done like this because zipfile module doesn't
    implement function to delete file.
    """
    tempdir = tempfile.mkdtemp()
    try:
        tempname = os.path.join(tempdir, 'new.zip')
        with zipfile.ZipFile(zipfname, 'r') as zipread:
            with zipfile.ZipFile(tempname, 'a') as zipwrite:
                for item in zipread.infolist():
                    if item.filename not in filenames:
                        data = zipread.read(item.filename)
                        zipwrite.writestr(item, data)
        shutil.move(tempname, zipfname)
    finally:
        shutil.rmtree(tempdir)


class SinolPackage(object):
    controller_name = 'oioioi.sinolpack.controllers.SinolProblemController'
    package_backend_name = 'oioioi.sinolpack.package.SinolPackageBackend'

    def __init__(self, path, original_filename=None):
        self.filename = original_filename or path
        if self.filename.lower().endswith('.tar.gz'):
            ext = '.tar.gz'
        else:
            ext = os.path.splitext(self.filename)[1]
        self.archive = Archive(path, ext)
        self.config = None
        self.problem = None
        self.main_problem_instance = None
        self.rootdir = None
        self.short_name = None
        self.env = None
        self.package = None
        self.time_limits = None
        self.memory_limits = None
        self.statement_memory_limit = None
        self.prog_archive = None
        self.extra_compilation_args = {
            'c': C_EXTRA_ARGS,
            'cpp': C_EXTRA_ARGS,
            'pas': PAS_EXTRA_ARGS,
        }
        self.use_make = settings.USE_SINOLPACK_MAKEFILES
        self.use_sandboxes = not settings.USE_UNSAFE_EXEC
        self.restrict_html = (
            settings.SINOLPACK_RESTRICT_HTML and not settings.USE_SINOLPACK_MAKEFILES
        )

    def identify(self):
        return self._find_main_dir() is not None

    def get_short_name(self):
        return self._find_main_dir()

    def _find_main_dir(self):
        """Looks for the directory which contains at least the in/ and out/
        subdirectories. Only one such directory should be found.
        Otherwise None is returned.
        """

        dirs = list(map(os.path.normcase, self.archive.dirnames()))
        dirs = list(map(os.path.normpath, dirs))
        toplevel_dirs = set(f.split(os.sep)[0] for f in dirs)
        toplevel_dirs = list(filter(slug_re.match, toplevel_dirs))
        problem_dirs = []
        for dir in toplevel_dirs:
            for required_subdir in ('in', 'out'):
                if all(f.split(os.sep)[:2] != [dir, required_subdir] for f in dirs):
                    break
            else:
                problem_dirs.append(dir)
        if len(problem_dirs) == 1:
            return problem_dirs[0]

        return None

    def _save_to_field(self, field, file):
        basename = os.path.basename(filetracker_to_django_file(file).name)
        filename = os.path.join(self.rootdir, basename)
        get_client().get_file(file, filename)
        field.save(os.path.basename(filename), File(open(filename, 'rb')))
        get_client().delete_file(file)

    def _find_and_compile(
        self, suffix, command=None, cwd=None, log_on_failure=True, out_name=None
    ):
        if not command:
            command = suffix
        if self.use_make:
            renv = self._compile_using_make(command, cwd, suffix)
        else:
            renv = self._compile_matching_extension(command, out_name, suffix)

        if not renv and log_on_failure:
            logger.info("%s: no %s in package", self.filename, command)
        return renv

    def _compile_using_make(self, command, cwd, suffix):
        renv = None
        if glob.glob(
            os.path.join(self.rootdir, 'prog', '%s%s.*' % (self.short_name, suffix))
        ):
            logger.info("%s: %s", self.filename, command)
            renv = {}
            if not cwd:
                cwd = self.rootdir
            renv['stdout'] = execute('make %s' % (command), cwd=cwd).decode(
                'utf-8', 'replace'
            )
            logger.info(renv['stdout'])
        return renv

    def _compile_matching_extension(self, command, out_name, suffix):
        renv = None
        name = self.short_name + suffix
        lang_exts_list = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}).values()
        exts = [ext for lang_exts in lang_exts_list for ext in lang_exts]
        for ext in exts:
            src = os.path.join(self.rootdir, 'prog', '%s.%s' % (name, ext))
            if os.path.isfile(src):
                renv = self._compile(src, name, ext, out_name)
                logger.info("%s: %s", self.filename, command)
                break
        return renv

    def _compile(self, filename, prog_name, ext, out_name=None):
        client = get_client()
        source_name = '%s.%s' % (prog_name, ext)
        ft_source_name = client.put_file(
            _make_filename_in_job_dir(self.env, source_name), filename
        )

        if not out_name:
            out_name = _make_filename_in_job_dir(self.env, '%s.e' % prog_name)

        new_env = self._run_compilation_job(ext, ft_source_name, out_name)
        client.delete_file(ft_source_name)

        self._ensure_compilation_success(filename, new_env)

        # TODO Remeber about 'exec_info' when Java support is introduced.
        new_env['compiled_file'] = new_env['out_file']
        return new_env

    # This is a hack for szkopul backwards compatibility.
    # See settings.OVERRIDE_COMPILER_LANGS for more info.
    # Should be removed when szkopul removes older compilers.
    def _override_compiler(self, prefix, lang, compilation_job):
        if prefix != 'default':
            return

        name_map = {
            'c': 'C',
            'cpp': 'C++',
            'pas': 'Pascal',
            'java': 'Java',
            'py': 'Python'
        }

        if lang in name_map and lang in settings.OVERRIDE_COMPILER_LANGS:
            compilation_job['compiler'] = settings.DEFAULT_COMPILERS[name_map[lang]]

    def _run_compilation_job(self, ext, ft_source_name, out_name):
        compilation_job = self.env.copy()
        compilation_job['job_type'] = 'compile'
        compilation_job['task_priority'] = TASK_PRIORITY
        compilation_job['source_file'] = ft_source_name
        compilation_job['out_file'] = out_name
        lang = ext
        compilation_job['language'] = lang
        if self.use_sandboxes:
            prefix = 'default'
        else:
            prefix = 'system'
        compilation_job['compiler'] = prefix + '-' + lang
        self._override_compiler(prefix, lang, compilation_job)

        if not self.use_make and self.prog_archive:
            compilation_job['additional_archive'] = self.prog_archive
        add_extra_files(
            compilation_job, self.problem, additional_args=self.extra_compilation_args
        )
        new_env = run_sioworkers_job(compilation_job)
        return new_env

    def _ensure_compilation_success(self, filename, new_env):
        compilation_message = new_env.get('compiler_output', '')
        compilation_result = new_env.get('result_code', 'CE')
        if compilation_result != 'OK':
            logger.warning(
                "%s: compilation of file %s failed with code %s",
                self.filename,
                filename,
                compilation_result,
            )
            logger.warning(
                "%s: compiler output: %r", self.filename, compilation_message
            )

            raise ProblemPackageError(
                _(
                    "Compilation of file %(filename)s "
                    "failed. Compiler output: "
                    "%(output)s"
                )
                % {'filename': filename, 'output': compilation_message}
            )

    def _make_ins(self, re_string):
        env = self._find_and_compile('ingen')
        if env and not self.use_make:
            env['job_type'] = 'ingen'
            env['task_priority'] = TASK_PRIORITY
            env['exe_file'] = env['compiled_file']
            env['re_string'] = re_string
            env['use_sandboxes'] = self.use_sandboxes
            try:
                env['ingen_mem_limit'] = settings.INGEN_MEMORY_LIMIT
            except Exception:
                pass
            env['collected_files_path'] = _make_filename_in_job_dir(self.env, 'in')

            renv = run_sioworkers_job(env)

            if renv['return_code'] != 0:
               raise ProblemPackageError(_("Ingen failed: %r") % renv)

            get_client().delete_file(env['compiled_file'])
            return renv['collected_files']

        return {}

    def unpack(self, env, package):
        self.short_name = self.get_short_name()
        self.env = env
        self.package = package

        self._create_problem_or_reuse_if_exists(self.package.problem)
        return self._extract_and_process_package()

    def _create_problem_or_reuse_if_exists(self, existing_problem):
        if existing_problem:
            self.problem = existing_problem
            self._ensure_short_name_equality_with(existing_problem)
        else:
            self.problem = self._create_problem_instance()
            problem_site = ProblemSite(problem=self.problem, url_key=generate_key())
            problem_site.save()
            self.problem.problem_site = problem_site

        self.main_problem_instance = self.problem.main_problem_instance
        self.problem.package_backend_name = self.package_backend_name
        self.problem.save()

    def _ensure_short_name_equality_with(self, existing_problem):
        if existing_problem.short_name != self.short_name:
            raise ProblemPackageError(
                _(
                    "Tried to replace problem "
                    "'%(oldname)s' with '%(newname)s'. For safety, changing "
                    "problem short name is not possible."
                )
                % dict(oldname=existing_problem.short_name, newname=self.short_name)
            )

    def _create_problem_instance(self):
        author_username = self.env.get('author')
        if author_username:
            author = User.objects.get(username=author_username)
        else:
            author = None

        return Problem.create(
            legacy_name=self.short_name,
            short_name=self.short_name,
            controller_name=self.controller_name,
            contest=self.package.contest,
            visibility=(
                Problem.VISIBILITY_PUBLIC
                if author is None
                else self.env.get('visibility', Problem.VISIBILITY_FRIENDS)
            ),
            author=author,
        )

    def _extract_and_process_package(self):
        tmpdir = tempfile.mkdtemp()
        logger.info("%s: tmpdir is %s", self.filename, tmpdir)
        try:
            self.archive.extract(to_path=tmpdir)
            self.rootdir = os.path.join(tmpdir, self.short_name)
            self._process_package()

            return self.problem
        finally:
            shutil.rmtree(tmpdir)
            if self.prog_archive:
                get_client().delete_file(self.prog_archive)

    def _describe_processing_error(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except PackageProcessingError as error:
                # Reraising this way allows us to retrieve the full stack trace
                # that would otherwise be screened by the try...except clause.

                six.reraise(PackageProcessingError, error, sys.exc_info()[2])

            except Exception:
                # Reraising as a custom exception allows us to attach extra
                # information about the raising operation to the exception

                error = PackageProcessingError(
                    func.__name__, func.__doc__.split("\n\n")[0]
                )

                six.reraise(PackageProcessingError, error, sys.exc_info()[2])

        return wrapper

    def _process_package(self):
        self._process_config_yml()
        self._detect_full_name()
        self._detect_full_name_translations()
        self._detect_library()
        self._process_extra_files()
        if self.use_make:
            self._extract_makefiles()
        else:
            self._save_prog_dir()
        self._process_statements()
        self._generate_tests()
        self._process_checkers()
        self._process_model_solutions()
        self._process_attachments()
        self._save_original_package()

    @_describe_processing_error
    def _process_config_yml(self):
        """Parses the ``config.yml`` file from the package.

        Extracted information is then saved for later use.
        """
        config_file = os.path.join(self.rootdir, 'config.yml')
        instance, created = ExtraConfig.objects.get_or_create(problem=self.problem)
        if os.path.isfile(config_file):
            # In Python 3, io.open is an alias for the builtin open() function.
            instance.config = io.open(config_file, 'r', encoding='utf-8').read()
        else:
            instance.config = ''
        instance.save()
        self.config = instance.parsed_config

    @_describe_processing_error
    def _detect_full_name(self):
        """Sets the problem's full name from the ``config.yml`` (key ``title``)
        or from the ``title`` tag in the LaTeX source file.
        The ``config.yml`` file takes precedence over the LaTeX source.

        Example of how the ``title`` tag may look like:
        \title{A problem}
        """
        if 'title' in self.config:
            self.problem.legacy_name = self.config['title']
            self.problem.save()
            return

        source = os.path.join(self.rootdir, 'doc', self.short_name + 'zad.tex')
        if os.path.isfile(source):
            text = open(source, 'rb').read()
            r = re.search(br'^[^%]*\\title{(.+)}', text, re.MULTILINE)
            if r is not None:
                self.problem.legacy_name = _decode(r.group(1), text)
                self.problem.save()

    @_describe_processing_error
    def _detect_full_name_translations(self):
        """Creates problem's full name translations from the ``config.yml``
        (keys matching the pattern ``title_[a-z]{2}``, where ``[a-z]{2}`` represents
        two-letter language code defined in ``settings.py``), if any such key is given.
        """
        for lang_code, lang in settings.LANGUAGES:
            key = 'title_%s' % lang_code
            if key in self.config:
                ProblemName.objects.get_or_create(
                    problem=self.problem, name=self.config[key], language=lang_code
                )

    @_describe_processing_error
    def _detect_library(self):
        """Finds if the problem has a library defined in ``config.yml``.

        Tries to read a library name (filename library should be given
        during compilation) from the ``config.yml`` (key ``library``).

        If there is no such key, assumes that a library is not needed.
        """
        if 'library' in self.config and self.config['library']:
            instance, _created = LibraryProblemData.objects.get_or_create(
                problem=self.problem
            )
            instance.libname = self.config['library']
            instance.save()
            logger.info("Library %s needed for this problem.", instance.libname)
        else:
            LibraryProblemData.objects.filter(problem=self.problem).delete()

    @_describe_processing_error
    def _process_extra_files(self):
        """Looks for extra compilation files specified in ``config.yml``."""
        ExtraFile.objects.filter(problem=self.problem).delete()
        files = list(self.config.get('extra_compilation_files', ()))
        for lang_files in self.config.get('extra_execution_files', {}).values():
            files.extend(lang_files)
        not_found = self._find_and_save_files(set(files))
        if not_found:
            raise ProblemPackageError(
                _("Expected extra files %r not found in prog/") % (not_found)
            )

    def _find_and_save_files(self, files):
        """Saves files in the database.

        :param files: List of expected files.
        :return: List of files that were not found.
        """
        not_found = []
        for filename in files:
            fn = os.path.join(self.rootdir, 'prog', filename)
            if not os.path.isfile(fn):
                not_found.append(filename)
            else:
                instance = ExtraFile(problem=self.problem, name=filename)
                instance.file.save(filename, File(open(fn, 'rb')))
        return not_found

    def _extract_makefiles(self):
        sinol_makefiles_tgz = os.path.join(
            os.path.dirname(__file__), 'files', 'sinol-makefiles.tgz'
        )
        Archive(sinol_makefiles_tgz).extract(to_path=self.rootdir)

        makefile_in = os.path.join(self.rootdir, 'makefile.in')
        if not os.path.exists(makefile_in):
            with open(makefile_in, 'w') as f:
                f.write('MODE=wer\n')
                f.write('ID=%s\n' % (self.short_name,))
                f.write('SIG=xxxx000\n')

    @_describe_processing_error
    def _save_prog_dir(self):
        """Creates an archive to store compiled programs."""
        prog_dir = os.path.join(self.rootdir, 'prog')
        if not os.path.isdir(prog_dir):
            return
        archive_name = 'compilation-dir-archive'
        archive = shutil.make_archive(
            os.path.join(self.rootdir, archive_name), format="zip", root_dir=prog_dir
        )
        self.prog_archive = get_client().put_file(
            _make_filename_in_job_dir(self.env, archive), archive
        )

    @_describe_processing_error
    def _process_statements(self):
        """Creates a problem statement from html or pdf source.

        If `USE_SINOLPACK_MAKEFILES` is set to True in the OIOIOI settings,
        the pdf file will be compiled from a LaTeX source.
        """
        docdir = os.path.join(self.rootdir, 'doc')
        if not os.path.isdir(docdir):
            logger.warning("%s: no docdir", self.filename)
            return

        # pylint: disable=maybe-no-member
        self.problem.statements.all().delete()

        lang_prefs = [''] + ['-' + l[0] for l in settings.STATEMENT_LANGUAGES]

        if self.use_make:
            self._compile_latex_docs(docdir)

        for lang in lang_prefs:
            htmlzipfile = os.path.join(
                docdir, self.short_name + 'zad' + lang + '.html.zip'
            )
            if os.path.isfile(htmlzipfile):
                if self._html_disallowed():
                    raise ProblemPackageError(
                        _(
                            "You cannot upload package with "
                            "problem statement in HTML. "
                            "Try again using PDF format."
                        )
                    )

                self._force_index_encoding(htmlzipfile)
                statement = ProblemStatement(problem=self.problem, language=lang[1:])
                statement.content.save(
                    self.short_name + lang + '.html.zip', File(open(htmlzipfile, 'rb'))
                )

            pdffile = os.path.join(docdir, self.short_name + 'zad' + lang + '.pdf')

            if os.path.isfile(pdffile):
                statement = ProblemStatement(problem=self.problem, language=lang[1:])
                statement.content.save(
                    self.short_name + lang + '.pdf', File(open(pdffile, 'rb'))
                )

        if not self.problem.statements.exists():
            logger.warning("%s: no problem statement", self.filename)

    def _force_index_encoding(self, htmlzipfile):
        """Ensures index.html file is utf-8 encoded, if cannot apply
        this encoding raise
        :class:`~oioioi.problems.package.ProblemPackageError`.
        """
        with zipfile.ZipFile(htmlzipfile, 'r') as archive, archive.open(
            'index.html'
        ) as index:

            data = index.read()
            # First, we check if index.html is utf-8 encoded.
            # If it is - nothing to do.
            try:
                data.decode('utf8')
            # We accept iso-8859-2 encoded files, but django doesn't
            # so index.html has to be translated to utf-8.
            except UnicodeDecodeError:
                try:
                    data = data.decode('iso-8859-2').encode('utf8')
                except (UnicodeDecodeError, UnicodeEncodeError):
                    raise ProblemPackageError(
                        _("index.html has to be utf8 or iso8859-2 encoded")
                    )
                # We have to remove index.html from the archive and
                # then add the translated file to archive because
                # zipfile module doesn't implement editing files
                # inside archive.
                _remove_from_zip(htmlzipfile, 'index.html')
                with zipfile.ZipFile(htmlzipfile, 'a') as new_archive:
                    new_archive.writestr('index.html', data)

    def _compile_latex_docs(self, docdir):
        # fancyheadings.sty looks like a rarely available LaTeX package...
        src_fancyheadings = os.path.join(
            os.path.dirname(__file__), 'files', 'fancyheadings.sty'
        )
        dst_fancyheadings = os.path.join(docdir, 'fancyheadings.sty')
        if not os.path.isfile(dst_fancyheadings):
            shutil.copyfile(src_fancyheadings, dst_fancyheadings)

        # Extract sinol.cls and oilogo.*, but do not overwrite if they
        # already exist (-k).
        sinol_cls_tgz = os.path.join(
            os.path.dirname(__file__), 'files', 'sinol-cls.tgz'
        )
        execute(['tar', '-C', docdir, '--skip-old-files','-zxf',  sinol_cls_tgz], cwd=docdir)

        try:
            execute('make', cwd=docdir)
        except ExecuteError:
            logger.warning(
                "%s: failed to compile statement", self.filename, exc_info=True
            )

    @_describe_processing_error
    def _generate_tests(self, total_score_if_auto=100):
        """Generates tests for the problem.

        First, time and memory limits are obtained from ``config.yml``.
        Then, the judge system attempts to obtain a generic memory limit
        from the problem statement.

        Next, test instances are created, using input files (``*.in``)
        provided with the package and `ingen` (the input file generator)
        where applicable (``ingen``-generated tests may replace ``*.in`` files
        contained in the package if their respective names coincide).

        If `USE_SINOLPACK_MAKEFILES` is set to True in the OIOIOI settings,
        output files (``*.out``) will also be generated at this point,
        based on the model solution's output (on condition that its source
        code is included within the package).

        The next step is veryfing whether the sum of time limits over
        all tests does not exceed the maximum defined by the OIOIOI
        installation's owner.

        If an input verifier is provided, it will then assert that all
        ``*.in`` files generated are valid, and abort the upload in case of failure.

        Here the ``*.out`` files will be generated if `USE_SINOLPACK_MAKEFILES`
        is set to False, based on the model solution's output (on condition
        that its source code is included within the package).

        In the end, it is asserted that all tests have been correctly
        constructed, non-created tests are removed from the database
        and test scores are assigned to tests and testgroups based on
        the configuration from ``config.yml`` or set to default value
        if not specified.
        """
        self.time_limits = _stringify_keys(self.config.get('time_limits', {}))
        self.memory_limits = _stringify_keys(self.config.get('memory_limits', {}))
        self.statement_memory_limit = self._detect_statement_memory_limit()

        created_tests, outs_to_make, scored_groups = self._create_instances_for_tests()
        sum_of_time_limits = 0
        for test in created_tests:
            sum_of_time_limits += test.time_limit
        self._verify_time_limits(sum_of_time_limits)

        self._verify_inputs(created_tests)
        self._generate_test_outputs(created_tests, outs_to_make)
        self._validate_tests(created_tests)
        self._delete_non_existing_tests(created_tests)

        self._assign_scores(scored_groups, total_score_if_auto)
        self._process_language_override()

    def _detect_statement_memory_limit(self):
        """Returns the memory limit in the problem statement, converted to
        KiB or ``None``.
        """
        source = os.path.join(self.rootdir, 'doc', self.short_name + 'zad.tex')
        if os.path.isfile(source):
            with open(source, 'rb') as f:
                text = f.read()
            r = re.search(br'^[^%]*\\RAM{(\d+)}', text, re.MULTILINE)
            if r is not None:
                try:
                    value = int(r.group(1))
                    # In SIO1's tradition 66000 was used instead of 65536 etc.
                    # We're trying to cope with this legacy here.
                    return (value + (value + 31) // 32) * 1000
                except ValueError:
                    pass
        return None

    def _create_instances_for_tests(self):
        """Iterate through available test inputs.
        :return: Triple (created tests instances,
                         outs that have to be generated,
                         score groups (determined by test names))
        """
        indir = os.path.join(self.rootdir, 'in')
        outdir = os.path.join(self.rootdir, 'out')

        re_string = r'^(%s(([0-9]+)([a-z]?[a-z0-9]*))).in$' % (
            re.escape(self.short_name)
        )
        names_re = re.compile(re_string)

        collected_ins = self._make_ins(re_string)
        all_items = list(set(os.listdir(indir)) | set(collected_ins.keys()))

        created_tests = []
        outs_to_make = []
        scored_groups = set()

        if self.use_make and not self.config.get('no_outgen', False):
            self._find_and_compile('', command='outgen')

        for order, test in enumerate(sorted(all_items, key=naturalsort_key)):
            instance = self._process_test(
                test,
                order,
                names_re,
                indir,
                outdir,
                collected_ins,
                scored_groups,
                outs_to_make,
            )
            if instance:
                created_tests.append(instance)

        return created_tests, outs_to_make, scored_groups

    @_describe_processing_error
    def _verify_time_limits(self, time_limit_sum):
        """Checks whether the sum of test time limits does not exceed
        the allowed maximum.

        :raises: :class:`~oioioi.problems.package.ProblemPackageError`
        if sum of tests time limits exceeds the maximum defined in the
        `settings.py` file.
        """
        if time_limit_sum > settings.MAX_TEST_TIME_LIMIT_PER_PROBLEM:
            time_limit_sum_rounded = (time_limit_sum + 999) / 1000.0
            limit_seconds = settings.MAX_TEST_TIME_LIMIT_PER_PROBLEM / 1000.0

            raise ProblemPackageError(
                _(
                    "Sum of time limits for all tests is too big. It's %(sum)ds, "
                    "but it shouldn't exceed %(limit)ds."
                )
                % {'sum': time_limit_sum_rounded, 'limit': limit_seconds}
            )

    @_describe_processing_error
    def _verify_inputs(self, tests):
        """Checks if ``inwer`` exits with code 0 on all tests.

        :raises: :class:`~oioioi.problems.package.ProblemPackageError`
        otherwise.
        """
        env = self._find_and_compile('inwer')
        if env and not self.use_make:
            jobs = {}

            for test in tests:
                job = env.copy()
                job['job_type'] = 'inwer'
                job['task_priority'] = TASK_PRIORITY
                job['exe_file'] = env['compiled_file']
                job['in_file'] = django_to_filetracker_path(test.input_file)
                job['in_file_name'] = self.short_name + test.name + '.in'
                job['use_sandboxes'] = self.use_sandboxes
                jobs[test.name] = job

            jobs = run_sioworkers_jobs(jobs)
            get_client().delete_file(env['compiled_file'])

            for test_name, job in jobs.items():
                if job['result_code'] != 'OK':
                    raise ProblemPackageError(
                        _("Inwer failed on test %(test)s. Inwer output %(output)s")
                        % {'test': test_name, 'output': '\n'.join(job['stdout'])}
                    )

            logger.info("%s: inwer success", self.filename)

    def _generate_test_outputs(self, tests, outs_to_make):
        if not self.use_make:
            outs = self._make_outs(outs_to_make)
            for instance in tests:
                if instance.name in outs:
                    generated_out = outs[instance.name]
                    self._save_to_field(instance.output_file, generated_out['out_file'])

    @_describe_processing_error
    def _validate_tests(self, created_tests):
        """Checks if all tests have output files and that
        all tests have been successfully created.

        :raises: :class:`~oioioi.problems.package.ProblemPackageError`
        """
        for instance in created_tests:
            if not instance.output_file:
                raise ProblemPackageError(
                    _("Missing out file for test %s") % instance.name
                )
            try:
                instance.full_clean()
            except ValidationError as e:
                raise ProblemPackageError(e.messages[0])

    def _delete_non_existing_tests(self, created_tests):
        for test in Test.objects.filter(
            problem_instance=self.main_problem_instance
        ).exclude(id__in=[instance.id for instance in created_tests]):
            logger.info("%s: deleting test %s", self.filename, test.name)
            test.delete()

    @_describe_processing_error
    def _process_test(
        self,
        test,
        order,
        names_re,
        indir,
        outdir,
        collected_ins,
        scored_groups,
        outs_to_make,
    ):
        """Responsible for saving test in and out files,
        setting test limits, assigning test kinds and groups.

        :param test: Test name.
        :param order: Test number.
        :param names_re: Compiled regex to match test details from name.
               Should extract basename, test name,
               group number and test type.
        :param indir: Directory with tests inputs.
        :param outdir: Directory with tests outputs.
        :param collected_ins: List of inputs that were generated,
               not taken from archive as a file.
        :param scored_groups: Accumulator for score groups.
        :param outs_to_make: Accumulator for name of output files to
               be generated by model solution.
        :return: Test instance or None if name couldn't be matched.
        """
        match = names_re.match(test)
        if not match:
            if test.endswith('.in'):
                raise ProblemPackageError(_("Unrecognized test: %s") % (test))
            return None

        # Examples for odl0ocen.in:
        basename = match.group(1)  # odl0ocen
        name = match.group(2)  # 0ocen
        group = match.group(3)  # 0
        suffix = match.group(4)  # ocen

        instance, created = Test.objects.get_or_create(
            problem_instance=self.main_problem_instance, name=name
        )

        inname_base = basename + '.in'
        inname = os.path.join(indir, inname_base)
        outname_base = basename + '.out'
        outname = os.path.join(outdir, outname_base)

        if test in collected_ins:
            self._save_to_field(instance.input_file, collected_ins[test])
        else:
            instance.input_file.save(inname_base, File(open(inname, 'rb')))

        if os.path.isfile(outname):
            instance.output_file.save(outname_base, File(open(outname), 'rb'))
        else:
            outs_to_make.append(
                (
                    _make_filename_in_job_dir(self.env, 'out/%s' % (outname_base)),
                    instance,
                )
            )

        if group == '0' or 'ocen' in suffix:
            # Example tests
            instance.kind = 'EXAMPLE'
            instance.group = name
        else:
            instance.kind = 'NORMAL'
            instance.group = group
            scored_groups.add(group)

        time_limit = self._get_time_limit(created, name, group)
        if time_limit:
            instance.time_limit = time_limit

        memory_limit = self._get_memory_limit(created, name, group)
        if memory_limit:
            instance.memory_limit = memory_limit

        instance.order = order
        instance.save()
        return instance

    @_describe_processing_error
    def _get_memory_limit(self, created, name, group):
        """If we find the memory limit specified anywhere in the package:
        either in the ``config.yml`` or in the problem statement
        then we overwrite potential manual changes.

        (In the future we should disallow editing memory limits
        if they were taken from the package).

        The memory limit is more important the more specific it is.
        In particular, the global memory limit is less important
        than the memory limit for a test group, while the memory limit
        for particular test is the most imporant.
        :return: Memory limit found in config or statement,
                 None otherwise.
        """
        if name in self.memory_limits:
            return self.memory_limits[name]
        if group in self.memory_limits:
            return self.memory_limits[group]
        if 'memory_limit' in self.config:
            return self.config['memory_limit']
        if self.statement_memory_limit is not None:
            return self.statement_memory_limit
        if created:
            return DEFAULT_MEMORY_LIMIT

        return None

    @_describe_processing_error
    def _get_time_limit(self, created, name, group):
        """If we find the time limit specified anywhere in in the ``config.yml``
        then we overwrite potential manual changes.

        The time limit is more important the more specific it is.
        In particular, the global time limit is less important
        than the time limit for a test group, while the time limit
        for particular test is the most imporant.
        :return: Time limit found in config, None otherwise.
        """
        if name in self.time_limits:
            return self.time_limits[name]
        if group in self.time_limits:
            return self.time_limits[group]
        if 'time_limit' in self.config:
            return self.config['time_limit']
        if created:
            return DEFAULT_TIME_LIMIT

        return None

    @_describe_processing_error
    def _make_outs(self, outs_to_make):
        """Compiles the model solution and executes it in order to generate
        test outputs.

        :return: Result from workers.
        """
        env = self._find_and_compile('', command='outgen')
        if not env:
            return {}

        jobs = {}
        for outname, test in outs_to_make:
            job = env.copy()
            job['job_type'] = 'exec' if self.use_sandboxes else 'unsafe-exec'
            job['task_priority'] = TASK_PRIORITY
            job['exe_file'] = env['compiled_file']
            job['upload_out'] = True
            job['in_file'] = django_to_filetracker_path(test.input_file)
            job['out_file'] = outname
            if test.memory_limit:
                job['exec_mem_limit'] = test.memory_limit
            jobs[test.name] = job

        jobs = run_sioworkers_jobs(jobs)
        get_client().delete_file(env['compiled_file'])
        return jobs

    @_describe_processing_error
    def _check_scores_from_config(self, scored_groups, config_scores):
        """Called if ``config.yml`` specifies scores for any tests.
        Makes sure that all scored tests are present in ``config.yml``
        and that nothing else is there.
        """

        for group in scored_groups:
            if int(group) not in config_scores:
                errormsg = _(
                    "Score for group '%(group_name)s' not found. "
                    "You must either provide scores for all groups "
                    "or not provide them at all "
                    "(to have them assigned automatically). "
                    "(Scored groups: %(scored_groups)s, "
                    "groups from config: %(config_groups)s)"
                ) % {
                    "group_name": group,
                    "scored_groups": list(scored_groups),
                    "config_groups": config_scores,
                }
                raise ProblemPackageError(errormsg)

        for group in config_scores:
            if str(group) not in scored_groups:
                errormsg = _(
                    "Score for group '%(group_name)s' "
                    "found in config, "
                    "but no such test group exists in scored groups. "
                    "You must either provide scores for all groups "
                    "or not provide them at all "
                    "(to have them assigned automatically). "
                    "(Scored groups: %(scored_groups)s, "
                    "groups from config: %(config_groups)s)"
                ) % {
                    "group_name": group,
                    "scored_groups": list(scored_groups),
                    "config_groups": config_scores,
                }
                raise ProblemPackageError(errormsg)

    @_describe_processing_error
    def _compute_scores_automatically(self, scored_groups, total_score):
        """If there are no testscores specified ``config.yml``, all groups
        get equal score, except few last groups that are given +1
        to compensate rounding error and match the total sum of ``total_score``.
        """
        if not scored_groups:
            return {}

        scores = {}
        num_groups = len(scored_groups)
        group_score = total_score // num_groups
        extra_score_groups = sorted(scored_groups, key=naturalsort_key)[
            num_groups - (total_score - num_groups * group_score) :
        ]
        for group in scored_groups:
            score = group_score
            if group in extra_score_groups:
                score += 1

            scores[group] = score

        return scores

    @_describe_processing_error
    def _assign_scores(self, scored_groups, total_score_if_auto):
        """Checks if there's a ``scores`` entry in config
        and sets scores according to that
        or assigns them automatically otherwise.
        """
        group_scores_from_config = self.config.get('scores', {})
        if group_scores_from_config:
            self._check_scores_from_config(scored_groups, group_scores_from_config)
            scores = group_scores_from_config
        else:
            scores = self._compute_scores_automatically(
                scored_groups, total_score_if_auto
            )

        Test.objects.filter(problem_instance=self.main_problem_instance).update(
            max_score=0
        )

        for group, score in scores.items():
            Test.objects.filter(
                problem_instance=self.main_problem_instance, group=group
            ).update(max_score=score)

    @_describe_processing_error
    def _process_language_override(self):
        """Checks if there's a `override_limits` entry in config
        and for existing tests, add additional limits overrides.
        Time limits are validated the same way it's validated
        in default package.
        """
        if 'override_limits' in self.config and self.config['override_limits']:
            overrides = self.config['override_limits']
            for lang in overrides:
                self._prepare_overrides(lang)
                new_rules = overrides[lang]
                self._set_memory_limit_overrides(lang, new_rules)
                self._set_time_limit_overrides(lang, new_rules)

    @_describe_processing_error
    def _prepare_overrides(self, lang):
        """Prepares overrides for specified language, initially setting
        to default limits.
        """
        tests = Test.objects.filter(problem_instance=self.main_problem_instance)
        for test in tests:
            LanguageOverrideForTest.objects.update_or_create(
                defaults={
                    'time_limit': test.time_limit,
                    'memory_limit': test.memory_limit,
                },
                test=test,
                language=lang,
            )

    @_describe_processing_error
    def _set_memory_limit_overrides(self, lang, rules):
        """Sets memory limits overrides for specific language."""

        if 'memory_limit' in rules:
            tests = Test.objects.filter(problem_instance=self.main_problem_instance)
            for test in tests:
                LanguageOverrideForTest.objects.filter(test=test, language=lang).update(
                    memory_limit=rules['memory_limit']
                )
        elif 'memory_limits' in rules:
            for group, limit in rules['memory_limits'].items():
                tests = Test.objects.filter(
                    problem_instance=self.main_problem_instance, group=group
                )
                for test in tests:
                    LanguageOverrideForTest.objects.filter(
                        test=test, language=lang
                    ).update(memory_limit=limit)

    @_describe_processing_error
    def _set_time_limit_overrides(self, lang, rules):
        """Sets time limits overrides for specific language."""
        if 'time_limit' in rules:
            tests = Test.objects.filter(problem_instance=self.main_problem_instance)
            for test in tests:
                LanguageOverrideForTest.objects.filter(test=test, language=lang).update(
                    time_limit=rules['time_limit']
                )
        elif 'time_limits' in rules:
            for group, limit in rules['time_limits'].items():
                tests = Test.objects.filter(
                    problem_instance=self.main_problem_instance, group=group
                )
                for test in tests:
                    LanguageOverrideForTest.objects.filter(
                        test=test, language=lang
                    ).update(time_limit=limit)

    @_describe_processing_error
    def _process_checkers(self):
        """Compiles an output checker and saves its binary."""
        checker_name = '%schk.e' % (self.short_name)
        out_name = _make_filename_in_job_dir(self.env, checker_name)
        instance = OutputChecker.objects.get_or_create(problem=self.problem)[0]
        env = self._find_and_compile(
            'chk',
            command=checker_name,
            cwd=os.path.join(self.rootdir, 'prog'),
            log_on_failure=False,
            out_name=out_name,
        )
        if not self.use_make and env:
            self._save_to_field(instance.exe_file, env['compiled_file'])
        else:
            instance.exe_file = self._find_checker_exec()
            instance.save()

    def _find_checker_exec(self):
        checker_prefix = os.path.join(self.rootdir, 'prog', self.short_name + 'chk')
        exe_candidates = [checker_prefix + '.e', checker_prefix + '.sh']
        for exe in exe_candidates:
            if os.path.isfile(exe):
                return File(open(exe, 'rb'))

        return None

    def _process_model_solutions(self):
        """Saves model solutions to the database."""
        ModelSolution.objects.filter(problem=self.problem).delete()

        progs = self._get_model_solutions_sources()

        # Dictionary -- kind_shortcut -> (order, full_kind_name)
        kinds = {'': (0, 'NORMAL'), 's': (1, 'SLOW'), 'b': (2, 'INCORRECT')}

        def modelsolutionssort_key(key):
            short_kind, name, _path = key
            return (kinds[short_kind][0], naturalsort_key(name[: name.index(".")]))

        for order, (short_kind, name, path) in enumerate(
            sorted(progs, key=modelsolutionssort_key)
        ):
            instance = ModelSolution(
                problem=self.problem,
                name=name,
                order_key=order,
                kind=kinds[short_kind][1],
            )

            instance.source_file.save(name, File(open(path, 'rb')))
            logger.info('%s: model solution: %s', self.filename, name)

    def _get_model_solutions_sources(self):
        """:return: Sources as tuples (kind_of_solution, filename,
        full path to file).
        """
        lang_exts_list = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}).values()
        extensions = [ext for lang_exts in lang_exts_list for ext in lang_exts]
        regex = r'^%s[0-9]*([bs]?)[0-9]*(_.*)?\.(' + '|'.join(extensions) + ')'
        names_re = re.compile(regex % (re.escape(self.short_name),))
        progdir = os.path.join(self.rootdir, 'prog')
        progs = [
            (x[0].group(1), x[1], x[2])
            for x in (
                (names_re.match(name), name, os.path.join(progdir, name))
                for name in os.listdir(progdir)
            )
            if x[0] and os.path.isfile(x[2])
        ]
        return progs

    def _process_attachments(self):
        """Removes previously added attachments for the problem,
        and saves new ones from the attachment directory.
        """
        problem_attachments = ProblemAttachment.objects.filter(problem=self.problem)
        if problem_attachments is not None:
            problem_attachments.delete()

        attachments_dir = os.path.join(self.rootdir, 'attachments')
        if not os.path.isdir(attachments_dir):
            return
        attachments = [
            attachment
            for attachment in os.listdir(attachments_dir)
            if os.path.isfile(os.path.join(attachments_dir, attachment))
        ]
        if len(attachments) == 0:
            return

        for attachment in attachments:
            path = os.path.join(attachments_dir, attachment)
            instance = ProblemAttachment(problem=self.problem, description=attachment)
            instance.content.save(attachment, File(open(path, 'rb')))
            logger.info('%s: attachment: %s', path, attachment)

    def _save_original_package(self):
        """Save instance of package that would be reused by other
        instances of this problem.
        """
        original_package, created = OriginalPackage.objects.get_or_create(
            problem=self.problem
        )
        original_package.problem_package = self.package
        original_package.save()

    def _html_disallowed(self):
        if not self.restrict_html:
            return False

        author_username = self.env.get('author')
        if author_username:
            author = User.objects.get(username=author_username)
        else:
            return True

        return not (author.is_superuser or author.has_perm('teachers.teacher'))


class SinolPackageCreator(object):
    """Responsible for packing SinolPackages."""

    def __init__(self, problem):
        self.problem = problem
        self.short_name = problem.short_name
        self.zip = None

    def pack(self):
        """:returns: Archive from original package if such file exists,
        otherwise new archive with test, statements and model solutions.
        """
        try:
            original_package = OriginalPackage.objects.get(problem=self.problem)
            if original_package.problem_package.package_file:
                return stream_file(original_package.problem_package.package_file)
        except OriginalPackage.DoesNotExist:
            pass

        return self._create_basic_archive()

    def _create_basic_archive(self):
        """Produce the most basic output: tests, statements, model solutions."""
        fd, tmp_filename = tempfile.mkstemp()
        try:
            self.zip = zipfile.ZipFile(os.fdopen(fd, 'wb'), 'w', zipfile.ZIP_DEFLATED)
            self._pack_statement()
            self._pack_tests()
            self._pack_model_solutions()
            self.zip.close()
            zip_filename = '%s.zip' % self.short_name
            return stream_file(File(open(tmp_filename, 'rb'), name=zip_filename))
        finally:
            os.unlink(tmp_filename)

    def _pack_statement(self):
        for statement in ProblemStatement.objects.filter(problem=self.problem):
            if not statement.content.name.endswith('.pdf'):
                continue
            if statement.language:
                filename = os.path.join(
                    self.short_name,
                    'doc',
                    '%szad-%s.pdf' % (self.short_name, statement.language),
                )
            else:
                filename = os.path.join(
                    self.short_name, 'doc', '%szad.pdf' % (self.short_name,)
                )
            self._pack_django_file(statement.content, filename)

    def _pack_django_file(self, django_file, arcname):
        """Packs file represented by
        :class:~`oioioi.filetracker.fields.FileField`
        """
        reader = django_file.file
        if hasattr(reader.file, 'name'):
            self.zip.write(reader.file.name, arcname)
        else:
            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, 'wb')
            try:
                shutil.copyfileobj(reader, fileobj)
                fileobj.close()
                self.zip.write(name, arcname)
            finally:
                os.unlink(name)

    def _pack_tests(self):
        # Takes tests from main_problem_instance
        for test in Test.objects.filter(
            problem_instance=self.problem.main_problem_instance
        ):
            basename = '%s%s' % (self.short_name, test.name)
            self._pack_django_file(
                test.input_file, os.path.join(self.short_name, 'in', basename + '.in')
            )
            self._pack_django_file(
                test.output_file,
                os.path.join(self.short_name, 'out', basename + '.out'),
            )

    def _pack_model_solutions(self):
        for solution in ModelSolution.objects.filter(problem=self.problem):
            self._pack_django_file(
                solution.source_file,
                os.path.join(self.short_name, 'prog', solution.name),
            )


class SinolPackageBackend(ProblemPackageBackend):
    """Backend that use
    :class:`~oioioi.sinolpack.package.SinolPackage` to unpack
    and :class:`~oioioi.sinolpack.package.SinolPackageCreator` to pack
    sinol packages.
    """

    description = _("Sinol Package")
    package_class = SinolPackage

    def identify(self, path, original_filename=None):
        return SinolPackage(path, original_filename).identify()

    def get_short_name(self, path, original_filename=None):
        return SinolPackage(path, original_filename).get_short_name()

    def unpack(self, env):
        package = ProblemPackage.objects.get(id=env['package_id'])
        with tempfile.NamedTemporaryFile() as tmpfile:
            shutil.copyfileobj(package.package_file.file, tmpfile)
            tmpfile.flush()
            problem = self.package_class(
                tmpfile.name, package.package_file.name
            ).unpack(env, package)
            env['problem_id'] = problem.id
        return env

    def pack(self, problem):
        return SinolPackageCreator(problem).pack()
