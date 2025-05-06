from django.urls import path
from django.urls import include

from oioioi.programs import views

app_name = 'programs'

userout_patterns = [
    path(
        'generate/one/<int:testreport_id>/',
        views.generate_user_output_view,
        name='generate_user_output',
    ),
    path(
        'generate/all/<int:submission_report_id>/',
        views.generate_user_output_view,
        name='generate_user_output',
    ),
    path(
        'download/one/<int:testreport_id>/',
        views.download_user_one_output_view,
        name='download_user_output',
    ),
    path(
        'download/all/<int:submission_report_id>/',
        views.download_user_all_output_view,
        name='download_user_output',
    ),
]

urlpatterns = [
    path(
        'tests/<int:test_id>/in/',
        views.download_input_file_view,
        name='download_input_file',
    ),
    path(
        'tests/<int:test_id>/out/',
        views.download_output_file_view,
        name='download_output_file',
    ),
    path(
        'checker/<int:checker_id>/',
        views.download_checker_exe_view,
        name='download_checker_file',
    ),
    path('userout/', include(userout_patterns)),
    path(
        's/<int:submission_id>/source/',
        views.show_submission_source_view,
        name='show_submission_source',
    ),
    path(
        's/<int:submission_id>/download/',
        views.download_submission_source_view,
        name='download_submission_source',
    ),
    path(
        's/<int:submission_id>/diffsave/',
        views.save_diff_id_view,
        name='save_diff_id',
    ),
    path(
        'diff/<int:submission1_id>/<int:submission2_id>/',
        views.source_diff_view,
        name='source_diff',
    ),
    path(
        'get_compiler_hints/',
        views.get_compiler_hints_view,
        name='get_compiler_hints',
    ),
    path(
        'get_language_hints/',
        views.get_language_hints_view,
        name='get_language_hints',
    ),
]
