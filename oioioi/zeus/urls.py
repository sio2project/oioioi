from django.urls import re_path

from oioioi.zeus import views

app_name = "zeus"

noncontest_patterns = [
    re_path(
        r"^s/(?P<saved_environ_id>[-:a-zA-Z0-9]+)/push_grade/"
        r"(?P<signature>[\w\d:-]+)/$",
        views.push_grade,
        name="zeus_push_grade_callback",
    ),
]
