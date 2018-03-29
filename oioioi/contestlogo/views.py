from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from django.views.decorators.http import condition

from oioioi.contestlogo.models import ContestIcon, ContestLogo
from oioioi.filetracker.utils import stream_file


def last_change(request, image_object):
    return image_object.updated_at


@condition(last_modified_func=last_change)
def stream_if_changed(request, image_object):
    return stream_file(image_object.image)


@cache_control(max_age=1200)
def logo_image_view(request):
    logo = get_object_or_404(ContestLogo, contest=request.contest.id)
    return stream_if_changed(request, logo)


@cache_control(max_age=1200)
def icon_image_view(request, icon_id):
    icon = get_object_or_404(ContestIcon, id=icon_id)
    return stream_if_changed(request, icon)
