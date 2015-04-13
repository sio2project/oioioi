from django.template.loader import render_to_string
from oioioi.gamification.miniprofile import miniprofile_row_registry


def miniprofile_processor(request):
    if request.user.is_authenticated():
        rendered_rows = [row(request) for row in miniprofile_row_registry]
        return {'extra_body_miniprofile': render_to_string(
                    'gamification/miniprofile.html',
                    {'rows': rendered_rows})}
    else:
        return {}
