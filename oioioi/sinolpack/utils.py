import six

from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.sinolpack.models import ExtraConfig, ExtraFile


def add_extra_files(environ, problem, additional_args=None):
    try:
        config = ExtraConfig.objects.get(problem=problem).parsed_config
    except ExtraConfig.DoesNotExist:
        config = {}

    lang = environ['language']
    extra_args = config.get('extra_compilation_args', {}).get(lang, [])
    if isinstance(extra_args, six.string_types):
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
