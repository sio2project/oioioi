from django.conf.urls import include, url

from oioioi.programs import views

userout_patterns = [
    url(r'^generate/one/(?P<testreport_id>\d+)/$',
        views.generate_user_output_view, name='generate_user_output'),
    url(r'^generate/all/(?P<submission_report_id>\d+)/$',
        views.generate_user_output_view, name='generate_user_output'),
    url(r'^download/one/(?P<testreport_id>\d+)/$',
        views.download_user_one_output_view, name='download_user_output'),
    url(r'^download/all/(?P<submission_report_id>\d+)/$',
        views.download_user_all_output_view, name='download_user_output'),
]

urlpatterns = [
    url(r'^tests/(?P<test_id>\d+)/in/$', views.download_input_file_view,
        name='download_input_file'),
    url(r'^tests/(?P<test_id>\d+)/out/$', views.download_output_file_view,
        name='download_output_file'),
    url(r'^checker/(?P<checker_id>\d+)/$', views.download_checker_exe_view,
        name='download_checker_file'),
    url(r'^userout/', include(userout_patterns)),

    url(r'^s/(?P<submission_id>\d+)/source/$',
        views.show_submission_source_view,
        name='show_submission_source'),
    url(r'^s/(?P<submission_id>\d+)/download/$',
        views.download_submission_source_view,
        name='download_submission_source'),
    url(r'^s/(?P<submission_id>\d+)/diffsave/$',
        views.save_diff_id_view, name='save_diff_id'),
    url(r'^diff/(?P<submission1_id>\d+)/(?P<submission2_id>\d+)/$',
        views.source_diff_view, name='source_diff'),
]
