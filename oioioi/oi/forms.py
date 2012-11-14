# coding: utf-8

from django import forms
from django.forms import ValidationError
from django.forms.extras.widgets import SelectDateWidget
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from oioioi.oi.models import OIRegistration, PROVINCES, School, Region
import datetime

class RegionForm(forms.ModelForm):
    class Meta:
        model = Region

    def clean_short_name(self):
        if self.request_contest \
                and Region.objects.filter(contest=self.request_contest,
                short_name=self.cleaned_data['short_name']).exists():
            raise ValidationError(_("Region with this name already exists."))
        return self.cleaned_data['short_name']

def city_options(province):
    cities = School.objects.filter(province=province).order_by('city') \
            .distinct().values_list('city', flat=True)
    cities = zip(cities, cities)
    cities.insert(0, ('', "-- Wybierz miasto --"))
    return cities

def school_options(province, city):
    schools = School.objects.filter(province=province, city=city) \
            .order_by('name').only('name', 'address')
    schools = [(s.id, u'%s (%s)' % (s.name, s.address)) for s in schools]
    schools.insert(0, ('', "-- Wybierz szkołę --"))
    return schools

class SchoolSelect(forms.Select):
    def render(self, name, value, attrs=None):
        school = None
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

        provinces = [('', "-- Wybierz województwo --")] + list(PROVINCES)
        cities = city_options(province)
        schools = school_options(province, city)

        attr = {'name': name, 'id': 'id_' + name}
        options = [('_province', provinces, province), ('_city', cities, city),
                   ('',schools, school_id)]
        selects = {'attr': attr, 'options' : options}

        return render_to_string('forms/school_select_form.html', selects)

class OIRegistrationForm(forms.ModelForm):
    class Meta:
        model = OIRegistration
        exclude = ['participant']

    class Media:
        css = {'all': ('oi/reg.css',)}
        js = ('oi/reg.js',)

    def __init__(self, *args, **kwargs):
        super(OIRegistrationForm, self).__init__(*args, **kwargs)

        this_year = datetime.date.today().year
        years = reversed(range(this_year - 100, this_year + 1))
        self.fields['birthday'].widget = SelectDateWidget(years=years)

        self.fields['t_shirt_size'].widget.attrs['class'] = 'input-small'
        self.fields['school'].widget = SchoolSelect()
        self.fields['class_type'].widget.attrs['class'] = 'input-xlarge'

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise forms.ValidationError(_("Terms not accepted"))
        return True

