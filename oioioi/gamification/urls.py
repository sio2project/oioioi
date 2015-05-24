from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.gamification.views',
    url(r'^profile/$', 'profile_view', name='view_current_profile'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/$', 'profile_view',
        name='view_profile'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/send_request$',
        'send_friendship_request_view', name='send_friendship_request'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/remove_friend$',
        'remove_friend_view', name='remove_friend'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/accept_request$',
        'accept_friendship_request_view', name='accept_friendship_request'),
    url(r'^profile/(?P<username>[a-zA-Z0-9_@\+\.\-]+)/refuse_request$',
        'refuse_friendship_request_view', name='refuse_friendship_request'),
    url(r'^check_user_exists/$', 'check_user_exists_view',
        name='check_user_exists'),
    url(r'user_problem_exp/(?P<problem_id>\d+)/$', 'user_problem_exp_view',
        name='user_problem_exp'),
)
