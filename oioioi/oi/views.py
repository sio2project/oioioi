from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse
from oioioi.oi.forms import SchoolSelect, city_options, school_options


def cities_view(request):
    if 'province' not in request.REQUEST:
        raise SuspiciousOperation
    province = request.REQUEST['province']
    options = city_options(province)
    return HttpResponse(SchoolSelect().render_options(options, []))


def schools_view(request):
    if 'province' not in request.REQUEST or 'city' not in request.REQUEST:
        raise SuspiciousOperation
    province = request.REQUEST['province']
    city = request.REQUEST['city']
    options = school_options(province, city)
    return HttpResponse(SchoolSelect().render_options(options, []))
