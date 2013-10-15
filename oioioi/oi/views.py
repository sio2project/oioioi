from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse, SimpleTemplateResponse
from django.views.decorators.http import require_POST

from oioioi.base.permissions import not_anonymous, enforce_condition
from oioioi.oi.forms import SchoolSelect, city_options, school_options, \
        AddSchoolForm
from oioioi.oi.models import School


@enforce_condition(not_anonymous)
def cities_view(request):
    if 'province' not in request.REQUEST:
        raise SuspiciousOperation
    province = request.REQUEST['province']
    options = city_options(province)
    return HttpResponse(SchoolSelect().render_options(options, []))


@enforce_condition(not_anonymous)
def schools_view(request):
    if 'province' not in request.REQUEST or 'city' not in request.REQUEST:
        raise SuspiciousOperation
    province = request.REQUEST['province']
    city = request.REQUEST['city']
    options = school_options(province, city)
    return HttpResponse(SchoolSelect().render_options(options, []))


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
                return redirect('participants_register',
                                contest_id=request.contest.id)
            else:
                return redirect('default_contest_view',
                                contest_id=request.contest.id)
    else:
        form = AddSchoolForm()
    return TemplateResponse(request, 'forms/add_school_form.html',
                            {'form': form})


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
        schools = list(schools.filter(qobj)[:num_hints]) + \
                list(schools.filter(~qobj)[:num_hints])

    schools = schools[:num_hints]

    if schools:
        return SimpleTemplateResponse('oi/schools_similar_confirm.html',
                                  {'schools': schools})
    else:
        return HttpResponse('')
