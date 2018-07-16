import logging

from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.sinolpack.models import ExtraConfig, ExtraFile
from oioioi.evalmgr import tasks

logger = logging.getLogger(__name__)


def add_extra_execution_files(environ):
    try:
        config = ExtraConfig.objects.get(
            problem_id=environ.get('problem_id')
        ).parsed_config
    except ExtraConfig.DoesNotExist:
        config = {}

    lang = environ.get('language')
    for _, job in environ.get('tests', {}).items():
        extra_args = config.get('extra_execution_args', {}).get(lang, [])
        if isinstance(extra_args, str):
            extra_args = [extra_args]
        # here we allow to pass an empty argument by setting it to "" as bool([""])=True
        if extra_args:
            job['extra_execution_args'] = extra_args

        extra_file_names = config.get('extra_execution_files', {}).get(lang, [])
        if isinstance(extra_file_names, str):
            extra_file_names = [extra_file_names]
        extra_file_names = set(extra_file_names)
        if extra_file_names:
            extra_files = ExtraFile.objects.filter(
                problem_id=environ.get('problem_id'), name__in=extra_file_names
            ).all()
            if len(extra_file_names) != len(extra_files):
                raise RuntimeError(
                    'Did not find expected extra files: ' + ', '.join(extra_file_names)
                )
            job['extra_execution_files'] = dict(
                (ef.name, django_to_filetracker_path(ef.file)) for ef in extra_files
            )
    return environ


def add_extra_files(environ, problem, additional_args=None):
    try:
        config = ExtraConfig.objects.get(problem=problem).parsed_config
    except ExtraConfig.DoesNotExist:
        config = {}

    lang = environ['language']
    extra_args = config.get('extra_compilation_args', {}).get(lang, [])
    if isinstance(extra_args, str):
        extra_args = [extra_args]
    if additional_args:
        extra_args.extend(additional_args.get(lang, []))
    if extra_args:
        environ['extra_compilation_args'] = extra_args

    extra_file_names = config.get('extra_compilation_files', [])
    extra_files = ExtraFile.objects.filter(
        problem=problem, name__in=extra_file_names
    ).all()
    if len(extra_file_names) != len(extra_files):
        raise RuntimeError(
            'Did not find expected extra files: ' + ', '.join(extra_file_names)
        )
    environ['extra_files'] = dict(
        (ef.name, django_to_filetracker_path(ef.file)) for ef in extra_files
    )

    if 'recipe' in environ:
        try:
            tasks.add_after_recipe_entry(
                environ,
                'collect_tests',
                (
                    'add_extra_execution_files',
                    'oioioi.sinolpack.utils.add_extra_execution_files',
                ),
            )
        except IndexError:
            tasks.add_after_recipe_entry(
                environ,
                'make_test',
                (
                    'add_extra_execution_files',
                    'oioioi.sinolpack.utils.add_extra_execution_files',
                ),
            )
