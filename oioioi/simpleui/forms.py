from django import forms
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.contests.models import ProblemInstance, Round
from oioioi.problems.models import ProblemAttachment, Tag
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


class AttachmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AttachmentForm, self).__init__(*args, **kwargs)
        try:
            self.instance = kwargs['instance']
            self.fields['content'].name = self.instance.content.name.split('/')[-1]
            self.fields['content'].exists = True  # Instance is bound.
        except KeyError:
            self.fields['content'].exists = False
            # Instance isn't bound. This means that the form has been submitted
            # but there've been validation errors and the current field is a
            # newly added one.

    # Updates the link field to the one containing given contest_id.
    def update_link(self, contest_id):
        if self.instance is None or self.instance.id is None:
            self.fields['content'].link = '#'
            return
        self.fields['content'].link = reverse(
            'problem_attachment',
            kwargs={'contest_id': contest_id, 'attachment_id': self.instance.id},
        )

    class Meta(object):
        model = ProblemAttachment
        fields = ('content', 'id', 'description')
        readonly_fields = ('content', 'id', 'description')


class TagForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TagForm, self).__init__(*args, **kwargs)
        try:
            self.instance = kwargs['instance']
            self.fields['name'].value = self.instance.name
            self.fields['name'].exists = True
        except KeyError:
            self.fields['name'].exists = False

    def validate_unique(self):
        # We only want to validate the value itself, not uniqueness, as
        # later we are going to create the object only if it does not exist
        pass

    class Meta(object):
        model = Tag
        fields = ('name', 'id')


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
