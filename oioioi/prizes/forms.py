from django import forms
from django.forms.models import BaseInlineFormSet
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from oioioi.prizes.models import Prize, PrizeGiving


class PrizeGivingForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = PrizeGiving

    redo = forms.BooleanField(label=_("redo"), required=False)

    def save(self, commit=True):
        instance = super(PrizeGivingForm, self).save(commit=False)

        kwargs = {'commit': commit}
        if self.cleaned_data['redo']:
            kwargs.update(force_reset=True, date=timezone.now())

        instance.update(**kwargs)
        return instance


class PrizeInlineFormSet(BaseInlineFormSet):
    @property
    def initial_forms(self):
        initial_forms = super(PrizeInlineFormSet, self).initial_forms

        # In admin change view some PrizeGivings could have already been
        # deleted what could have triggered deletion of the related Prizes
        # as well. Therefore we remove the corresponding Prize forms.

        contest = self.instance
        prizes = set(Prize.objects.filter(contest=contest))
        return [form for form in initial_forms if form.instance in prizes]
