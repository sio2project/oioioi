import datetime

from django import forms
from django.forms import ValidationError
from django.forms.widgets import SelectDateWidget
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from six.moves import range, zip

from oioioi.oi.models import PROVINCES, OIRegistration, School


class AddSchoolForm(forms.ModelForm):
    class Meta(object):
        model = School
        exclude = ['is_active', 'is_approved']


def city_options(province):
    cities = School.objects.filter(province=province, is_active=True) \
            .order_by('city').distinct().values_list('city', flat=True)
    cities = list(zip(cities, cities))
    cities.insert(0, ('', _("-- Choose city --")))
    return cities


def school_options(province, city):
    schools = School.objects.filter(province=province, city=city,
            is_active=True).order_by('name').only('name', 'address')
    schools = [(s.id, u'%s (%s)' % (s.name, s.address)) for s in schools]
    schools.insert(0, ('', _("-- Choose school --")))
    return schools


class SchoolSelect(forms.Select):
    def render(self, name, value, attrs=None):
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
        cities = city_options(province)
        schools = school_options(province, city)

        attr = {'name': name, 'id': 'id_' + name}
        options = [('_province', provinces, province), ('_city', cities, city),
                   ('', schools, school_id)]
        selects = {
            'attr': attr,
            'options': options,
            # Do not show 'add new' link in admin view. Hack.
            'show_add_new': 'oi_oiregistration' not in name,
        }

        return render_to_string('forms/school_select_form.html', selects)


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
        self.fields['class_type'].widget.attrs['class'] = 'input-xlarge'

    def set_terms_accepted_text(self, terms_accepted_phrase):
        if terms_accepted_phrase is None:
            self.fields['terms_accepted'].label = _("terms accepted")
        else:
            self.fields['terms_accepted'].label = \
                mark_safe(terms_accepted_phrase.text)

    def clean_school(self):
        school = self.cleaned_data['school']
        if not school.is_active:
            raise forms.ValidationError(_("This school is no longer active."))
        return school

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise forms.ValidationError(_("Terms not accepted"))
        return True
