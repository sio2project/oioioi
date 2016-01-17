from django import forms
from django.utils.translation import ugettext_lazy as _

from oioioi.newsfeed.models import News


class NewsForm(forms.ModelForm):
    class Meta(object):
        model = News
        fields = ['title', 'content']

    title = forms.CharField(
            label=_("Title"),
            max_length=255,
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

    content = forms.CharField(
            label=_("Content"),
            widget=forms.Textarea(attrs={'class': 'input-xxlarge',
                                         'rows': 10}))
