from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.contests.models import ProblemInstance, Round
from oioioi.programs.models import Test


class ProblemInstanceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProblemInstanceForm, self).__init__(*args, **kwargs)
        self.fields['round'].queryset = Round.objects.filter(
            contest=kwargs['instance'].contest
        )

    class Meta(object):
        model = ProblemInstance
        fields = ['submissions_limit', 'round', 'id']


class TestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TestForm, self).__init__(*args, **kwargs)
        instance = kwargs['instance']
        self.fields['input_file'].link = self.input_file_link(instance)
        self.fields['output_file'].link = self.output_file_link(instance)

    class Meta(object):
        model = Test
        fields = (
            'name',
            'time_limit',
            'memory_limit',
            'max_score',
            'kind',
            'input_file',
            'output_file',
            'is_active',
            'id',
        )
        readonly_fields = ('name', 'kind', 'group', 'input_file', 'output_file', 'id')
        ordering = ('kind', 'order', 'name')

    def input_file_link(self, instance):
        if instance.id is not None:
            href = reverse('download_input_file', kwargs={'test_id': instance.id})
            return make_html_link(href, _("in"))
        return None

    input_file_link.short_description = _("Input file")

    def output_file_link(self, instance):
        if instance.id is not None:
            href = reverse('download_output_file', kwargs={'test_id': instance.id})
            return make_html_link(href, _("out"))
        return None

    output_file_link.short_description = _("Output/hint file")
