from django.urls import path

from oioioi.testrun import views

app_name = 'testrun'

contest_patterns = [
    path('testrun_submit/', views.testrun_submit_view, name='testrun_submit'),
    path(
        's/<int:submission_id>/tr/input/',
        views.show_input_file_view,
        name='get_testrun_input',
    ),
    path(
        's/<int:submission_id>/tr/output/',
        views.show_output_file_view,
        name='get_testrun_output',
    ),
    path(
        's/<int:submission_id>/tr/output/<int:testrun_report_id>/',
        views.show_output_file_view,
        name='get_specific_testrun_output',
    ),
    path(
        's/<int:submission_id>/tr/input/download/',
        views.download_input_file_view,
        name='download_testrun_input',
    ),
    path(
        's/<int:submission_id>/tr/output/download/',
        views.download_output_file_view,
        name='download_testrun_output',
    ),
    path(
        's/<int:submission_id>/tr/output/<int:testrun_report_id>/download/',
        views.download_output_file_view,
        name='download_specific_testrun_output',
    ),
]
