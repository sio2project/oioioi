from django import template
from django.conf import settings
from django.contrib.staticfiles import finders


def find_common_media():
    for finder in finders.get_finders():
        for path, _storage in finder.list([]):
            if path.startswith(settings.COMMON_MEDIA_PREFIX):
                yield path


def generate_styles():
    lines = []
    for path in find_common_media():
        if path.endswith(".css"):
            lines.append(f'<link charset="utf-8" rel="stylesheet" type="text/css" href="{{{{ STATIC_URL }}}}{path}">')
        elif path.endswith(".scss"):
            lines.append(f'<link charset="utf-8" rel="stylesheet" type="text/x-scss" href="{{{{ STATIC_URL }}}}{path}">')
    return "\n".join(lines)


def generate_scripts():
    lines = []
    for path in find_common_media():
        if path.endswith(".js"):
            lines.append(f'<script type="text/javascript" src="{{{{ STATIC_URL }}}}{path}"></script>')
    return "\n".join(lines)


register = template.Library()

_cache = {}


def common_media_tag(template_generator, context):
    if template_generator in _cache:
        return _cache[template_generator]
    t = template.Template(template_generator())
    value = t.render(context)
    if not settings.DEBUG:
        _cache[template_generator] = value
    return value


def common_styles_tag(context):
    return common_media_tag(generate_styles, context)


def common_scripts_tag(context):
    return common_media_tag(generate_scripts, context)


register.simple_tag(common_styles_tag, takes_context=True, name="common_styles")
register.simple_tag(common_scripts_tag, takes_context=True, name="common_scripts")
