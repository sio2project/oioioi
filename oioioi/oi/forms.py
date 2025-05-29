import datetime

from django import forms
from django.forms import ValidationError
from django.forms.widgets import SelectDateWidget
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.oi.models import PROVINCES, OIRegistration, School


class AddSchoolForm(forms.ModelForm):
    class Meta(object):
        model = School
        exclude = ['is_active', 'is_approved']


def city_options(all_schools, province):
    cities = (
        all_schools.filter(province=province)
        .order_by('city')
        .distinct()
        .values_list('city', flat=True)
    )
    cities = list(zip(cities, cities))
    cities.insert(0, ('', _("-- Choose city --")))
    return cities


def school_options(all_schools, province, city):
    schools = (
        all_schools.filter(province=province, city=city)
        .order_by('name')
        .only('name', 'address')
    )
    schools = [(s.id, u'%s (%s)' % (s.name, s.address)) for s in schools]
    schools.insert(0, ('', _("-- Choose school --")))
    return schools


class SchoolSelect(forms.Select):
    def __init__(self, is_contest_with_coordinator=False, is_coordinator=False, *args, **kwargs):
        super(SchoolSelect, self).__init__(*args, **kwargs)
        self.is_contest_with_coordinator = is_contest_with_coordinator
        self.is_coordinator = is_coordinator

    def render(self, name, value, attrs=None, renderer=None):
        # check if this is the default renderer
        if renderer is not None and not isinstance(
            renderer, forms.renderers.DjangoTemplates
        ):
            raise AssertionError
        school_id = -1
        province = ''
        city = ''
        if value:
            try:
                school = School.objects.get(id=value)
                school_id = school.id
                province = school.province
                city = school.city
            except School.DoesNotExist:
                pass

        provinces = [('', _("-- Choose province --"))] + list(PROVINCES)
        cities = city_options(self.get_schools(), province)
        schools = school_options(self.get_schools(), province, city)

        attr = {'name': name, 'id': 'id_' + name}
        options = [
            ('_province', provinces, province),
            ('_city', cities, city),
            ('', schools, school_id),
        ]
        selects = {
            'attr': attr,
            'options': options,
            'is_contest_with_coordinator': self.is_contest_with_coordinator,
            'is_coordinator': self.is_coordinator,
        }

        return render_to_string('forms/school_select_form.html', selects)

    @staticmethod
    def get_schools():
        return School.objects.filter(is_active=True)


class OIRegistrationForm(forms.ModelForm):
    class Meta(object):
        model = OIRegistration
        exclude = ['participant']

    class Media(object):
        css = {'all': ('oi/reg.css',)}
        js = ('oi/reg.js',)

    def __init__(self, *args, **kwargs):
        super(OIRegistrationForm, self).__init__(*args, **kwargs)

        this_year = datetime.date.today().year
        years = list(reversed(range(this_year - 100, this_year + 1)))
        self.fields['birthday'].widget = SelectDateWidget(years=years)
        self.fields['school'].widget = SchoolSelect()

    def set_terms_accepted_text(self, terms_accepted_phrase):
        if terms_accepted_phrase is None:
            self.fields['terms_accepted'].label = _("terms accepted")
        else:
            self.fields['terms_accepted'].label = mark_safe(terms_accepted_phrase.text)

    def clean_school(self):
        school = self.cleaned_data['school']
        if not school.is_active:
            raise forms.ValidationError(_("This school is no longer active."))
        return school

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise forms.ValidationError(_("Terms not accepted"))
        return True
