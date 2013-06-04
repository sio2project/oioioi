from django.contrib.auth.signals import user_logged_in


def set_first_view_after_logging_flag(sender, user, request, **kwargs):
    request.session['first_view_after_logging'] = True

user_logged_in.connect(set_first_view_after_logging_flag)
