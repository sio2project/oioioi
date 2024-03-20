from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.utils import is_contest_admin
from oioioi.dashboard.registry import dashboard_headers_registry
from oioioi.oi.controllers import OIRegistrationController
from oioioi.oi.forms import AddSchoolForm, SchoolSelect, city_options, school_options
from oioioi.oi.models import School
from oioioi.participants.utils import is_participant


@dashboard_headers_registry.register_decorator(order=10)
def registration_notice_fragment(request):
    rc = request.contest.controller.registration_controller()
    if (
        isinstance(rc, OIRegistrationController)
        and request.user.is_authenticated
        and not is_contest_admin(request)
        and not is_participant(request)
        and rc.can_register(request)
    ):
        return render_to_string('oi/registration_notice.html', request=request)
    else:
        return None


@require_GET
@enforce_condition(not_anonymous)
def cities_view(request):
    if 'province' not in request.GET:
        raise SuspiciousOperation
    province = request.GET['province']
    options = city_options(province)
    return HttpResponse(SchoolSelect(choices=options).render_options([]))


@require_GET
@enforce_condition(not_anonymous)
def schools_view(request):
    if 'province' not in request.GET or 'city' not in request.GET:
        raise SuspiciousOperation
    province = request.GET['province']
    city = request.GET['city']
    options = school_options(province, city)
    return HttpResponse(SchoolSelect(choices=options).render_options([]))


@enforce_condition(not_anonymous)
def add_school_view(request):
    if request.method == 'POST':
        form = AddSchoolForm(request.POST)
        if form.is_valid():
            school = form.save(commit=False)
            school.is_approved = False
            school.save()
            if 'oi_oiregistrationformdata' in request.session:
                data = request.session['oi_oiregistrationformdata']
                data['school'] = school.id
                request.session['oi_oiregistrationformdata'] = data
                return redirect('participants_register', contest_id=request.contest.id)
            else:
                return redirect('default_contest_view', contest_id=request.contest.id)
    else:
        form = AddSchoolForm()
    return TemplateResponse(request, 'forms/add_school_form.html', {'form': form})


@enforce_condition(not_anonymous)
def choose_school_view(request, school_id):
    if not School.objects.filter(id=school_id, is_active=True).exists():
        raise Http404

    if 'oi_oiregistrationformdata' in request.session:
        data = request.session['oi_oiregistrationformdata']
        data['school'] = school_id
        # Explicitly mark session data as dirty
        request.session['oi_oiregistrationformdata'] = data
        return redirect('participants_register', contest_id=request.contest.id)
    else:
        return redirect('default_contest_view', contest_id=request.contest.id)


@require_POST
@enforce_condition(not_anonymous)
def schools_similar_view(request):
    schools = School.objects.filter(is_active=True)
    num_hints = getattr(settings, 'NUM_HINTS', 10)

    if 'postal_code' in request.POST and request.POST['postal_code']:
        schools = schools.filter(postal_code=request.POST['postal_code'])
    elif 'city' in request.POST and request.POST['city']:
        schools = schools.filter(city=request.POST['city'])
    elif 'province' in request.POST and request.POST['province']:
        schools = schools.filter(province=request.POST['province'])

    if 'address' in request.POST and request.POST['address']:
        address = request.POST['address']
        qobj = Q(address=address)
        for w in address.split():
            qobj |= Q(address__contains=w)
        # priority for schools with a matching part of the address
        schools = list(schools.filter(qobj)[:num_hints]) + list(
            schools.filter(~qobj)[:num_hints]
        )

    schools = schools[:num_hints]

    if schools:
        return SimpleTemplateResponse(
            'oi/schools_similar_confirm.html', {'schools': schools}
        )
    else:
        return HttpResponse('')
