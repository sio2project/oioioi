import glob
import logging
import re
import shutil
import tempfile
import os
import zipfile
import chardet

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import slug_re
from django.utils.translation import ugettext as _
from django.core.files import File
from django.contrib.auth.models import User

from oioioi.base.utils import naturalsort_key, generate_key
from oioioi.base.utils.archive import Archive
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.problems.models import Problem, ProblemStatement, ProblemPackage, \
        ProblemSite
from oioioi.problems.package import ProblemPackageBackend, \
        ProblemPackageError
from oioioi.programs.models import Test, OutputChecker, ModelSolution, \
        LibraryProblemData
from oioioi.sinolpack.models import ExtraConfig, ExtraFile, OriginalPackage
from oioioi.sinolpack.utils import add_extra_files
from oioioi.filetracker.utils import stream_file, django_to_filetracker_path, \
        filetracker_to_django_file
from oioioi.filetracker.client import get_client
from oioioi.sioworkers.jobs import run_sioworkers_job, run_sioworkers_jobs

logger = logging.getLogger(__name__)

DEFAULT_TIME_LIMIT = 10000
DEFAULT_MEMORY_LIMIT = 66000
C_EXTRA_ARGS = ['-Wall', '-Wno-unused-result', '-Werror']
PAS_EXTRA_ARGS = ['-Ci', '-Cr', '-Co', '-gl']


def _stringify_keys(dictionary):
    return dict((str(k), v) for k, v in dictionary.iteritems())


def _determine_encoding(title, file):
    r = re.search(r'\\documentclass\[(.+)\]{sinol}', file)
    encoding = 'latin2'

    if r is not None and 'utf8' in r.group(1):
        encoding = 'utf8'
    else:
        result = chardet.detect(title)
        if result['encoding'] == 'utf-8':
            encoding = 'utf-8'

    return encoding


def _decode(title, file):
    encoding = _determine_encoding(title, file)
    return title.decode(encoding)


def _make_filename(env, base_name):
    unpack_dir = '/unpack/%s' % (env['package_id'])
    env['unpack_dir'] = unpack_dir
    if 'job_id' not in env:
        env['job_id'] = 'local'
    return '%s/%s-%s' % (env['unpack_dir'], env['job_id'], base_name)


# Removes files from zip file by creating new zip file with all
# the files except the files to remove. Then the old file is removed.
# It has to be done like this because zipfile module doesn't
# implement function to delete file.
def _remove_from_zip(zipfname, *filenames):
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
        self.extra_compilation_args = \
                {'c': C_EXTRA_ARGS, 'cpp': C_EXTRA_ARGS, 'pas': PAS_EXTRA_ARGS}
        self.use_make = settings.USE_SINOLPACK_MAKEFILES
        self.use_sandboxes = not settings.USE_UNSAFE_EXEC

    def identify(self):
        return self._find_main_folder() is not None

    def get_short_name(self):
        return self._find_main_folder()

    def _find_main_folder(self):
        # Looks for the only folder which has at least the in/ and out/
        # subfolders.
        #
        # Note that depending on the archive type, there may be or
        # may not be entries for the folders themselves in
        # self.archive.filenames()

        files = map(os.path.normcase, self.archive.filenames())
        files = map(os.path.normpath, files)
        toplevel_folders = set(f.split(os.sep)[0] for f in files)
        toplevel_folders = filter(slug_re.match, toplevel_folders)
        problem_folders = []
        for folder in toplevel_folders:
            for required_subfolder in ('in', 'out'):
                if all(f.split(os.sep)[:2] != [folder, required_subfolder]
                       for f in files):
                    break
            else:
                problem_folders.append(folder)
        if len(problem_folders) == 1:
            return problem_folders[0]

    def _process_config_yml(self):
        config_file = os.path.join(self.rootdir, 'config.yml')
        instance, created = \
                ExtraConfig.objects.get_or_create(problem=self.problem)
        if os.path.isfile(config_file):
            instance.config = open(config_file, 'r').read()
        else:
            instance.config = ''
        instance.save()
        self.config = instance.parsed_config

    def _detect_full_name(self):
        """Sets the problem's full name from the ``config.yml`` (key ``title``)
           or from the ``title`` tag in the LateX source file.

           Example of how the ``title`` tag may look like:
           \title{A problem}
        """
        if 'title' in self.config:
            self.problem.name = self.config['title']
            self.problem.save()
            return

        source = os.path.join(self.rootdir, 'doc', self.short_name + 'zad.tex')
        if os.path.isfile(source):
            text = open(source, 'r').read()
            r = re.search(r'^[^%]*\\title{(.+)}', text, re.MULTILINE)
            if r is not None:
                self.problem.name = _decode(r.group(1), text)
                self.problem.save()

    def _detect_statement_memory_limit(self):
        """Returns the memory limit in the problem statement, converted to
           KiB or ``None``.
        """
        source = os.path.join(self.rootdir, 'doc', self.short_name + 'zad.tex')
        if os.path.isfile(source):
            text = open(source, 'r').read()
            r = re.search(r'^[^%]*\\RAM{(\d+)}', text, re.MULTILINE)
            if r is not None:
                try:
                    value = int(r.group(1))
                    # In SIO1's tradition 66000 was used instead of 65536 etc.
                    # We're trying to cope with this legacy here.
                    return (value + (value + 31) / 32) * 1000
                except ValueError:
                    pass
        return None

    def _save_prog_dir(self):
        prog_dir = os.path.join(self.rootdir, 'prog')
        if not os.path.isdir(prog_dir):
            return
        archive_name = 'compilation-dir-archive'
        archive = shutil.make_archive(
                os.path.join(self.rootdir, archive_name), format="zip",
                root_dir=prog_dir)
        self.prog_archive = get_client().put_file(
                _make_filename(self.env, archive), archive)

    def _find_and_save_files(self, files):
        not_found = []
        for filename in files:
            fn = os.path.join(self.rootdir, 'prog', filename)
            if not os.path.isfile(fn):
                not_found.append(filename)
            else:
                instance = ExtraFile(problem=self.problem, name=filename)
                instance.file.save(filename, File(open(fn, 'rb')))
        return not_found

    def _process_extra_files(self):
        ExtraFile.objects.filter(problem=self.problem).delete()
        files = list(self.config.get('extra_compilation_files', ()))
        not_found = self._find_and_save_files(files)
        if not_found:
            raise ProblemPackageError(
                    _("Expected extra files %r not found in prog/")
                    % (not_found))

    def _save_to_field(self, field, file):
        basename = os.path.basename(filetracker_to_django_file(file).name)
        filename = os.path.join(self.rootdir, basename)
        get_client().get_file(file, filename)
        field.save(os.path.basename(filename), File(open(filename, 'rb')))
        get_client().delete_file(file)

    def _extract_makefiles(self):
        sinol_makefiles_tgz = os.path.join(os.path.dirname(__file__),
                'files', 'sinol-makefiles.tgz')
        Archive(sinol_makefiles_tgz).extract(to_path=self.rootdir)

        makefile_in = os.path.join(self.rootdir, 'makefile.in')
        if not os.path.exists(makefile_in):
            with open(makefile_in, 'w') as f:
                f.write('MODE=wer\n')
                f.write('ID=%s\n' % (self.short_name,))
                f.write('SIG=xxxx000\n')

    def _compile_docs(self, docdir):
        # fancyheadings.sty looks like a rarely available LaTeX package...
        src_fancyheadings = os.path.join(os.path.dirname(__file__), 'files',
                'fancyheadings.sty')
        dst_fancyheadings = os.path.join(docdir, 'fancyheadings.sty')
        if not os.path.isfile(dst_fancyheadings):
            shutil.copyfile(src_fancyheadings, dst_fancyheadings)

        # Extract sinol.cls and oilogo.*, but do not overwrite if they
        # already exist (-k).
        sinol_cls_tgz = os.path.join(os.path.dirname(__file__), 'files',
                'sinol-cls.tgz')
        execute(['tar', '-C', docdir, '-kzxf', sinol_cls_tgz], cwd=docdir)

        try:
            execute('make', cwd=docdir)
        except ExecuteError:
            logger.warning("%s: failed to compile statement", self.filename,
                    exc_info=True)

    def _process_statements(self):
        docdir = os.path.join(self.rootdir, 'doc')
        if not os.path.isdir(docdir):
            logger.warning("%s: no docdir", self.filename)
            return

        # pylint: disable=maybe-no-member
        self.problem.statements.all().delete()

        htmlzipfile = os.path.join(docdir, self.short_name + 'zad.html.zip')
        if os.path.isfile(htmlzipfile):
            with zipfile.ZipFile(htmlzipfile, 'r') as archive, \
                 archive.open('index.html') as index:

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
                          _("index.html has to be utf8 or iso8859-2 encoded"))
                    # We have to remove index.html from the archive and
                    # then add the translated file to archive because
                    # zipfile module doesn't implement editing files
                    # inside archive.
                    _remove_from_zip(htmlzipfile, 'index.html')
                    with zipfile.ZipFile(htmlzipfile, 'a') as new_archive:
                        new_archive.writestr('index.html', data)

            statement = ProblemStatement(problem=self.problem)
            statement.content.save(self.short_name + '.html.zip',
                    File(open(htmlzipfile, 'rb')))

        pdffile = os.path.join(docdir, self.short_name + 'zad.pdf')

        if self.use_make and not os.path.isfile(pdffile):
            self._compile_docs(docdir)

        if os.path.isfile(pdffile):
            statement = ProblemStatement(problem=self.problem)
            statement.content.save(self.short_name + '.pdf',
                    File(open(pdffile, 'rb')))
        else:
            logger.warning("%s: no problem statement", self.filename)

    def _compile(self, filename, prog_name, ext, out_name=None):
        client = get_client()
        source_name = '%s.%s' % (prog_name, ext)
        ft_source_name = client.put_file(_make_filename(self.env, source_name),
                filename)

        if not out_name:
            out_name = _make_filename(self.env, '%s.e' % prog_name)

        compilation_job = self.env.copy()
        compilation_job['job_type'] = 'compile'
        compilation_job['source_file'] = ft_source_name
        compilation_job['out_file'] = out_name
        lang = ext
        compilation_job['language'] = lang
        if self.use_sandboxes:
            prefix = 'default'
        else:
            prefix = 'system'
        compilation_job['compiler'] = prefix + '-' + lang
        if not self.use_make and self.prog_archive:
            compilation_job['additional_archive'] = self.prog_archive

        add_extra_files(compilation_job, self.problem,
                additional_args=self.extra_compilation_args)
        new_env = run_sioworkers_job(compilation_job)
        client.delete_file(ft_source_name)

        compilation_message = new_env.get('compiler_output', '')
        compilation_result = new_env.get('result_code', 'CE')
        if compilation_result != 'OK':
            logger.warning("%s: compilation of file %s failed with code %s",
                    self.filename, filename, compilation_result)
            logger.warning("%s: compiler output: %r", self.filename,
                    compilation_message)

            raise ProblemPackageError(_("Compilation of file %(filename)s "
                "failed. Compiler output: %(output)s") % {
                    'filename': filename, 'output': compilation_message})

        # TODO Remeber about 'exec_info' when Java support is introduced.
        new_env['compiled_file'] = new_env['out_file']
        return new_env

    def _find_and_compile(self, suffix, command=None, cwd=None,
            log_on_failure=True, out_name=None):
        renv = None
        if not command:
            command = suffix
        if self.use_make:
            if glob.glob(os.path.join(self.rootdir, 'prog',
                    '%s%s.*' % (self.short_name, suffix))):
                logger.info("%s: %s", self.filename, command)
                renv = {}
                if not cwd:
                    cwd = self.rootdir
                renv['stdout'] = execute('make %s' % (command), cwd=cwd)
                logger.info(renv['stdout'])
        else:
            name = self.short_name + suffix
            choices = (getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})). \
                    values()
            lang_exts = []
            for ch in choices:
                lang_exts.extend(ch)

            source = None
            for ext in lang_exts:
                src = os.path.join(self.rootdir, 'prog', '%s.%s' % (name, ext))
                if os.path.isfile(src):
                    source = src
                    extension = ext
                    break

            if source:
                renv = self._compile(source, name, extension, out_name)
                logger.info("%s: %s", self.filename, command)

        if not renv and log_on_failure:
            logger.info("%s: no %s in package", self.filename, command)
        return renv

    def _make_ins(self, re_string):
        env = self._find_and_compile('ingen')
        if env and not self.use_make:
            env['job_type'] = 'ingen'
            env['exe_file'] = env['compiled_file']
            env['re_string'] = re_string
            env['use_sandboxes'] = self.use_sandboxes
            env['collected_files_path'] = _make_filename(self.env, 'in')

            renv = run_sioworkers_job(env)
            get_client().delete_file(env['compiled_file'])
            return renv['collected_files']
        else:
            return {}

    def _make_outs(self, outs_to_make):
        env = self._find_and_compile('', command='outgen')
        if not env:
            return {}

        jobs = {}
        for outname, test in outs_to_make:
            job = env.copy()
            job['job_type'] = 'exec' if self.use_sandboxes else 'unsafe-exec'
            job['exe_file'] = env['compiled_file']
            job['upload_out'] = True
            job['in_file'] = django_to_filetracker_path(test.input_file)
            job['out_file'] = outname
            jobs[test.name] = job

        jobs = run_sioworkers_jobs(jobs)
        get_client().delete_file(env['compiled_file'])
        return jobs

    def _verify_ins(self, tests):
        env = self._find_and_compile('inwer')
        if env and not self.use_make:
            jobs = {}

            for test in tests:
                job = env.copy()
                job['job_type'] = 'inwer'
                job['exe_file'] = env['compiled_file']
                job['in_file'] = django_to_filetracker_path(test.input_file)
                job['use_sandboxes'] = self.use_sandboxes
                jobs[test.name] = job

            jobs = run_sioworkers_jobs(jobs)
            get_client().delete_file(env['compiled_file'])

            for test_name, job in jobs.iteritems():
                if job['result_code'] != 'OK':
                    raise ProblemPackageError(_("Inwer failed on test "
                        "%(test)s. Inwer output %(output)s") %
                        {'test': test_name, 'output': '\n'.join(job['stdout'])}
                        )

            logger.info("%s: inwer success", self.filename)

    def _assign_scores(self, scored_groups, total_score):
        Test.objects.filter(problem_instance=self.main_problem_instance) \
                .update(max_score=0)
        num_groups = len(scored_groups)
        group_score = total_score / num_groups
        extra_score_groups = sorted(scored_groups, key=naturalsort_key)[
                num_groups - (total_score - num_groups * group_score):]
        for group in scored_groups:
            score = group_score
            if group in extra_score_groups:
                score += 1
            Test.objects.filter(problem_instance=self.main_problem_instance,
                    group=group).update(max_score=score)

    def _process_test(self, test, order, names_re, indir, outdir,
            collected_ins, scored_groups, outs_to_make):
        match = names_re.match(test)
        if not match:
            if test.endswith('.in'):
                raise ProblemPackageError(_("Unrecognized test: %s") %
                        (test))
            return None

        # Examples for odl0ocen.in:
        basename = match.group(1)    # odl0ocen
        name = match.group(2)        # 0ocen
        group = match.group(3)       # 0
        suffix = match.group(4)      # ocen

        instance, created = Test.objects.get_or_create(
                problem_instance=self.main_problem_instance, name=name)

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
        outs_to_make.append((_make_filename(self.env,
                'out/%s' % (outname_base)), instance))

        if group == '0' or 'ocen' in suffix:
            # Example tests
            instance.kind = 'EXAMPLE'
            instance.group = name
        else:
            instance.kind = 'NORMAL'
            instance.group = group
            scored_groups.add(group)

        if created:
            instance.time_limit = self.time_limits.get(name,
                    DEFAULT_TIME_LIMIT)

        # If we find the memory limit specified anywhere in the package:
        # either in the config.yml or in the problem statement, then we
        # overwrite potential manual changes. (In the future we should
        # disallow editing memory limits if they were taken from the
        # package).
        if name in self.memory_limits:
            instance.memory_limit = self.memory_limits[name]
        elif 'memory_limit' in self.config:
            instance.memory_limit = self.config['memory_limit']
        elif self.statement_memory_limit is not None:
            instance.memory_limit = self.statement_memory_limit
        elif created:
            instance.memory_limit = DEFAULT_MEMORY_LIMIT

        instance.order = order
        instance.save()
        return instance

    def _generate_tests(self, total_score=100):

        indir = os.path.join(self.rootdir, 'in')
        outdir = os.path.join(self.rootdir, 'out')

        scored_groups = set()
        re_string = r'^(%s(([0-9]+)([a-z]?[a-z0-9]*))).in$' \
                % (re.escape(self.short_name))
        names_re = re.compile(re_string)

        self.time_limits = _stringify_keys(self.config.get('time_limits', {}))
        self.memory_limits = _stringify_keys(
                self.config.get('memory_limits', {}))
        self.statement_memory_limit = self._detect_statement_memory_limit()

        outs_to_make = []
        created_tests = []
        collected_ins = self._make_ins(re_string)
        all_items = list(set(os.listdir(indir)) | set(collected_ins.keys()))
        if self.use_make:
            self._find_and_compile('', command='outgen')

        # Find tests and create objects
        for order, test in enumerate(sorted(all_items, key=naturalsort_key)):
            instance = self._process_test(test, order, names_re, indir, outdir,
                    collected_ins, scored_groups, outs_to_make)
            if instance:
                created_tests.append(instance)

        # Check test inputs
        self._verify_ins(created_tests)

        # Generate outputs (safe upload only)
        if not self.use_make:
            outs = self._make_outs(outs_to_make)
            for instance in created_tests:
                if instance.name in outs:
                    generated_out = outs[instance.name]
                    self._save_to_field(instance.output_file,
                            generated_out['out_file'])

        # Validate tests
        for instance in created_tests:
            if not instance.output_file:
                raise ProblemPackageError(_("Missing out file for test %s") %
                        instance.name)
            try:
                instance.full_clean()
            except ValidationError as e:
                raise ProblemPackageError(e.messages[0])

        # Delete nonexistent tests
        for test in Test.objects.filter(
                problem_instance=self.main_problem_instance) \
                .exclude(id__in=[instance.id for instance in created_tests]):
            logger.info("%s: deleting test %s", self.filename, test.name)
            test.delete()

        # Assign scores
        if scored_groups:
            self._assign_scores(scored_groups, total_score)

    def _detect_library(self):
        """Finds if the problem has a library.

           Tries to read a library name (filename library should be given
           during compilation) from the ``config.yml`` (key ``library``).

           If there is no such key, assumes that a library is not needed.
        """
        if 'library' in self.config and self.config['library']:
            instance, _created = LibraryProblemData.objects \
                .get_or_create(problem=self.problem)
            instance.libname = self.config['library']
            instance.save()
            logger.info("Library %s needed for this problem.",
                        instance.libname)
        else:
            LibraryProblemData.objects.filter(problem=self.problem).delete()

    def _process_checkers(self):
        checker = None
        checker_name = '%schk.e' % (self.short_name)
        out_name = _make_filename(self.env, checker_name)
        instance = OutputChecker.objects.get(problem=self.problem)
        env = self._find_and_compile('chk',
                command=checker_name,
                cwd=os.path.join(self.rootdir, 'prog'),
                log_on_failure=False,
                out_name=out_name)
        if not self.use_make and env:
            self._save_to_field(instance.exe_file, env['compiled_file'])
        else:
            checker_prefix = os.path.join(self.rootdir, 'prog',
                    self.short_name + 'chk')
            exe_candidates = [
                    checker_prefix + '.e',
                    checker_prefix + '.sh',
                ]
            for exe in exe_candidates:
                if os.path.isfile(exe):
                    checker = File(open(exe, 'rb'))
                    instance.exe_file = checker
                    instance.save()
                    break
        if not checker:
            instance.exe_file = None
            instance.save()

    def _process_model_solutions(self):
        ModelSolution.objects.filter(problem=self.problem).delete()

        lang_exts_list = \
                getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}).values()
        extensions = [ext for lang_exts in lang_exts_list for ext in lang_exts]
        regex = r'^%s[0-9]*([bs]?)[0-9]*\.(' + \
                '|'.join(extensions) + ')'
        names_re = re.compile(regex % (re.escape(self.short_name),))
        progdir = os.path.join(self.rootdir, 'prog')

        progs = [(x[0].group(1), x[1], x[2]) for x in
                    ((names_re.match(name), name, os.path.join(progdir, name))
                    for name in os.listdir(progdir))
                if x[0] and os.path.isfile(x[2])]

        # Dictionary -- kind_shortcut -> (order, full_kind_name)
        kinds = {
                '': (0, 'NORMAL'),
                's': (1, 'SLOW'),
                'b': (2, 'INCORRECT'),
        }

        def modelsolutionssort_key(key):
            short_kind, name, _path = key
            return (kinds[short_kind][0],
                    naturalsort_key(name[:name.index(".")]))

        for order, (short_kind, name, path) in \
               enumerate(sorted(progs, key=modelsolutionssort_key)):
            instance = ModelSolution(problem=self.problem, name=name,
                                     order_key=order,
                                     kind=kinds[short_kind][1])

            instance.source_file.save(name, File(open(path, 'rb')))
            logger.info("%s: model solution: %s", self.filename, name)

    def _save_original_package(self):
        original_package, created = \
                OriginalPackage.objects.get_or_create(problem=self.problem)
        original_package.problem_package = self.package
        original_package.save()

    def process_package(self):
        self._process_config_yml()
        self._detect_full_name()
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
        self._save_original_package()

    def unpack(self, env, package):
        self.short_name = self._find_main_folder()
        self.env = env
        self.package = package
        existing_problem = self.package.problem
        if existing_problem:
            self.problem = existing_problem
            self.main_problem_instance = self.problem.main_problem_instance
            if existing_problem.short_name != self.short_name:
                raise ProblemPackageError(_("Tried to replace problem "
                    "'%(oldname)s' with '%(newname)s'. For safety, changing "
                    "problem short name is not possible.") %
                    dict(oldname=existing_problem.short_name,
                        newname=self.short_name))
        else:
            author_username = env.get('author')
            if author_username:
                author = User.objects.get(username=author_username)
            else:
                author = None

            self.problem = Problem.create(
                    name=self.short_name,
                    short_name=self.short_name,
                    controller_name=self.controller_name,
                    contest=self.package.contest,
                    is_public=(author is None),
                    author=author)
            problem_site = ProblemSite(problem=self.problem,
                                       url_key=generate_key())
            problem_site.save()
            self.problem.problem_site = problem_site
            self.main_problem_instance = self.problem.main_problem_instance

        self.problem.package_backend_name = self.package_backend_name
        self.problem.save()
        tmpdir = tempfile.mkdtemp()
        logger.info("%s: tmpdir is %s", self.filename, tmpdir)
        try:
            self.archive.extract(to_path=tmpdir)
            self.rootdir = os.path.join(tmpdir, self.short_name)
            self.process_package()

            return self.problem
        finally:
            shutil.rmtree(tmpdir)
            if self.prog_archive:
                get_client().delete_file(self.prog_archive)


class SinolPackageCreator(object):
    def __init__(self, problem):
        self.problem = problem
        self.short_name = problem.short_name
        self.zip = None

    def _pack_django_file(self, django_file, arcname):
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

    def _pack_statement(self):
        for statement in ProblemStatement.objects.filter(problem=self.problem):
            if not statement.content.name.endswith('.pdf'):
                continue
            if statement.language:
                filename = os.path.join(self.short_name, 'doc', '%szad-%s.pdf'
                        % (self.short_name, statement.language))
            else:
                filename = os.path.join(self.short_name, 'doc', '%szad.pdf'
                        % (self.short_name,))
            self._pack_django_file(statement.content, filename)

    def _pack_tests(self):
        # Takes tests from main_problem_instance
        for test in Test.objects.filter(
                problem_instance=self.problem.main_problem_instance):
            basename = '%s%s' % (self.short_name, test.name)
            self._pack_django_file(test.input_file,
                    os.path.join(self.short_name, 'in', basename + '.in'))
            self._pack_django_file(test.output_file,
                    os.path.join(self.short_name, 'out', basename + '.out'))

    def _pack_model_solutions(self):
        for solution in ModelSolution.objects.filter(problem=self.problem):
            self._pack_django_file(solution.source_file,
                    os.path.join(self.short_name, 'prog', solution.name))

    def pack(self):
        try:
            original_package = OriginalPackage.objects.get(
                    problem=self.problem)
            if original_package.problem_package.package_file:
                return stream_file(original_package.
                        problem_package.package_file)
        except OriginalPackage.DoesNotExist:
            pass

        # If the original package is not available, produce the most basic
        # output: tests, statements, model solutions.
        fd, tmp_filename = tempfile.mkstemp()
        try:
            self.zip = zipfile.ZipFile(os.fdopen(fd, 'wb'), 'w',
                    zipfile.ZIP_DEFLATED)
            self._pack_statement()
            self._pack_tests()
            self._pack_model_solutions()
            self.zip.close()
            zip_filename = '%s.zip' % self.short_name
            return stream_file(File(open(tmp_filename, 'rb'),
                    name=zip_filename))
        finally:
            os.unlink(tmp_filename)


class SinolPackageBackend(ProblemPackageBackend):
    description = _("Sinol Package")
    package_class = SinolPackage

    def identify(self, path, original_filename=None):
        return SinolPackage(path, original_filename).identify()

    def get_short_name(self, path, original_filename=None):
        return SinolPackage(path, original_filename) \
                .get_short_name()

    def unpack(self, env):
        package = ProblemPackage.objects.get(id=env['package_id'])
        with tempfile.NamedTemporaryFile() as tmpfile:
            shutil.copyfileobj(package.package_file.file, tmpfile)
            tmpfile.flush()
            problem = self.package_class(tmpfile.name,
                    package.package_file.name).unpack(env, package)
            env['problem_id'] = problem.id
        return env

    def pack(self, problem):
        return SinolPackageCreator(problem).pack()
